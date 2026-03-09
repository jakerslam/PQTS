"""Cross-venue dislocation detection and hedged routing planner."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from itertools import permutations
from typing import Any

from core.persistence import EventPersistenceStore


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@dataclass(frozen=True)
class VenueQuote:
    venue: str
    symbol: str
    bid: float
    ask: float
    bid_depth: float
    ask_depth: float
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DislocationOpportunity:
    symbol: str
    buy_venue: str
    sell_venue: str
    buy_ask: float
    sell_bid: float
    gross_edge_bps: float
    net_edge_bps: float
    estimated_roundtrip_cost_bps: float
    max_hedged_notional: float
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HedgedRoutingPlan:
    symbol: str
    enabled: bool
    reason: str
    opportunities: list[DislocationOpportunity]
    selected: DislocationOpportunity | None
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["opportunities"] = [item.to_dict() for item in self.opportunities]
        payload["selected"] = self.selected.to_dict() if self.selected is not None else None
        return payload


class CrossVenueDislocationPlanner:
    """Identify actionable cross-venue basis and return a hedged routing decision."""

    def __init__(
        self,
        *,
        min_net_edge_bps: float = 8.0,
        default_fee_bps: float = 2.0,
        slippage_buffer_bps: float = 1.5,
        persistence_store: EventPersistenceStore | None = None,
    ) -> None:
        self.min_net_edge_bps = max(float(min_net_edge_bps), 0.0)
        self.default_fee_bps = max(float(default_fee_bps), 0.0)
        self.slippage_buffer_bps = max(float(slippage_buffer_bps), 0.0)
        self._store = persistence_store

    def _normalize_quote(self, *, venue: str, symbol: str, row: dict[str, Any]) -> VenueQuote | None:
        price = _as_float(row.get("price"))
        spread = abs(_as_float(row.get("spread")))
        bid = _as_float(row.get("bid"))
        ask = _as_float(row.get("ask"))
        if bid <= 0.0 or ask <= 0.0:
            if price <= 0.0:
                return None
            half_spread = spread / 2.0
            if half_spread <= 0.0:
                half_spread = max(price * 0.0001, 1e-9)
            bid = price - half_spread
            ask = price + half_spread
        if bid <= 0.0 or ask <= 0.0 or ask <= bid:
            return None

        bid_depth = max(_as_float(row.get("bid_depth")), _as_float(row.get("volume_24h")))
        ask_depth = max(_as_float(row.get("ask_depth")), _as_float(row.get("volume_24h")))
        ts = str(row.get("timestamp") or _utc_now_iso())
        return VenueQuote(
            venue=str(venue),
            symbol=str(symbol),
            bid=float(bid),
            ask=float(ask),
            bid_depth=float(bid_depth),
            ask_depth=float(ask_depth),
            timestamp=ts,
        )

    def detect_opportunities(
        self,
        *,
        symbol: str,
        venue_quotes: dict[str, dict[str, Any]],
        fee_bps_by_venue: dict[str, float] | None = None,
        timestamp: str | None = None,
    ) -> list[DislocationOpportunity]:
        quotes: list[VenueQuote] = []
        for venue_name, row in sorted(dict(venue_quotes).items()):
            if not isinstance(row, dict):
                continue
            normalized = self._normalize_quote(venue=str(venue_name), symbol=symbol, row=row)
            if normalized is not None:
                quotes.append(normalized)

        fees = {str(k): max(float(v), 0.0) for k, v in dict(fee_bps_by_venue or {}).items()}
        ts = str(timestamp or _utc_now_iso())
        opportunities: list[DislocationOpportunity] = []
        for buy_quote, sell_quote in permutations(quotes, 2):
            if buy_quote.venue == sell_quote.venue:
                continue
            mid = max((buy_quote.ask + sell_quote.bid) / 2.0, 1e-9)
            gross_edge_bps = ((sell_quote.bid - buy_quote.ask) / mid) * 10000.0
            roundtrip_cost = (
                fees.get(buy_quote.venue, self.default_fee_bps)
                + fees.get(sell_quote.venue, self.default_fee_bps)
                + self.slippage_buffer_bps
            )
            net_edge_bps = gross_edge_bps - roundtrip_cost
            if net_edge_bps <= 0.0:
                continue

            max_qty = min(
                max(buy_quote.ask_depth, 0.0),
                max(sell_quote.bid_depth, 0.0),
            )
            max_hedged_notional = max_qty * buy_quote.ask
            opportunities.append(
                DislocationOpportunity(
                    symbol=str(symbol),
                    buy_venue=buy_quote.venue,
                    sell_venue=sell_quote.venue,
                    buy_ask=float(buy_quote.ask),
                    sell_bid=float(sell_quote.bid),
                    gross_edge_bps=float(gross_edge_bps),
                    net_edge_bps=float(net_edge_bps),
                    estimated_roundtrip_cost_bps=float(roundtrip_cost),
                    max_hedged_notional=float(max_hedged_notional),
                    timestamp=ts,
                )
            )

        opportunities.sort(key=lambda item: item.net_edge_bps, reverse=True)
        return opportunities

    def plan(
        self,
        *,
        symbol: str,
        venue_quotes: dict[str, dict[str, Any]],
        fee_bps_by_venue: dict[str, float] | None = None,
        timestamp: str | None = None,
    ) -> HedgedRoutingPlan:
        ts = str(timestamp or _utc_now_iso())
        opportunities = self.detect_opportunities(
            symbol=symbol,
            venue_quotes=venue_quotes,
            fee_bps_by_venue=fee_bps_by_venue,
            timestamp=ts,
        )
        selected = opportunities[0] if opportunities else None
        enabled = bool(selected and selected.net_edge_bps >= self.min_net_edge_bps)
        if selected is None:
            reason = "No positive net dislocation after costs."
        elif not enabled:
            reason = (
                f"Best net edge {selected.net_edge_bps:.2f}bps below min threshold "
                f"{self.min_net_edge_bps:.2f}bps."
            )
        else:
            reason = (
                f"Route hedge: buy {selected.buy_venue} / sell {selected.sell_venue} "
                f"at {selected.net_edge_bps:.2f}bps net edge."
            )

        plan = HedgedRoutingPlan(
            symbol=str(symbol),
            enabled=enabled,
            reason=reason,
            opportunities=opportunities,
            selected=selected if enabled else None,
            timestamp=ts,
        )
        if self._store is not None:
            self._store.append(
                category="cross_venue_dislocation_plans",
                payload=plan.to_dict(),
                timestamp=ts,
            )
        return plan

    def replay_plans(self, *, symbol: str | None = None) -> list[HedgedRoutingPlan]:
        if self._store is None:
            return []
        rows = self._store.read(category="cross_venue_dislocation_plans", limit=100000)
        plans: list[HedgedRoutingPlan] = []
        for row in reversed(rows):
            payload = dict(row.payload)
            if symbol is not None and str(payload.get("symbol")) != str(symbol):
                continue
            opportunities_raw = payload.get("opportunities", [])
            selected_raw = payload.get("selected")
            opportunities = [
                DislocationOpportunity(**item)
                for item in opportunities_raw
                if isinstance(item, dict)
            ]
            selected = DislocationOpportunity(**selected_raw) if isinstance(selected_raw, dict) else None
            plans.append(
                HedgedRoutingPlan(
                    symbol=str(payload.get("symbol", "")),
                    enabled=bool(payload.get("enabled", False)),
                    reason=str(payload.get("reason", "")),
                    opportunities=opportunities,
                    selected=selected,
                    timestamp=str(payload.get("timestamp", row.timestamp)),
                )
            )
        return plans
