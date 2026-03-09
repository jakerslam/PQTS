"""Informed-flow indicators and automated quote/size kill-switch decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from statistics import mean
from typing import Any, Iterable

from core.persistence import EventPersistenceStore
from execution.microstructure_features import extract_microstructure_features


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _trade_qty(trade: dict[str, Any]) -> float:
    for key in ("quantity", "qty", "size", "volume"):
        qty = _as_float(trade.get(key))
        if qty > 0.0:
            return qty
    signed_qty = _as_float(trade.get("signed_qty"))
    return abs(signed_qty)


def _trade_sign(trade: dict[str, Any]) -> float:
    signed_qty = _as_float(trade.get("signed_qty"))
    if signed_qty > 0.0:
        return 1.0
    if signed_qty < 0.0:
        return -1.0
    side = str(trade.get("side", "")).strip().lower()
    if side in {"buy", "b", "bid", "aggressive_buy", "long"}:
        return 1.0
    if side in {"sell", "s", "ask", "aggressive_sell", "short"}:
        return -1.0
    return 0.0


@dataclass(frozen=True)
class VPINEstimate:
    market_id: str
    lookback_trades: int
    bucket_volume: float
    bucket_count: int
    mean_bucket_imbalance: float
    vpin: float
    buy_volume: float
    sell_volume: float
    total_volume: float
    computed_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QuoteSizeDecision:
    market_id: str
    action: str
    severity: str
    quote_enabled: bool
    size_multiplier: float
    reason: str
    metrics: dict[str, float]
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class InformedFlowKillSwitch:
    """Derive VPIN-style flow stress and convert it into deterministic trade actions."""

    def __init__(
        self,
        *,
        persistence_store: EventPersistenceStore | None = None,
        lookback_trades: int = 200,
        bucket_volume: float = 100.0,
        vpin_reduce_threshold: float = 0.60,
        vpin_halt_threshold: float = 0.80,
        spread_reduce_bps: float = 20.0,
        spread_halt_bps: float = 50.0,
        min_side_depth_reduce_usd: float = 10000.0,
        min_side_depth_halt_usd: float = 3000.0,
        max_depth_participation_reduce: float = 0.08,
        max_depth_participation_halt: float = 0.20,
        min_size_multiplier: float = 0.10,
    ) -> None:
        if lookback_trades <= 0:
            raise ValueError("lookback_trades must be positive.")
        if bucket_volume <= 0:
            raise ValueError("bucket_volume must be positive.")
        if not (0.0 <= vpin_reduce_threshold < vpin_halt_threshold <= 1.0):
            raise ValueError("VPIN thresholds must satisfy 0 <= reduce < halt <= 1.")
        self._store = persistence_store
        self.lookback_trades = int(lookback_trades)
        self.bucket_volume = float(bucket_volume)
        self.vpin_reduce_threshold = float(vpin_reduce_threshold)
        self.vpin_halt_threshold = float(vpin_halt_threshold)
        self.spread_reduce_bps = float(spread_reduce_bps)
        self.spread_halt_bps = float(spread_halt_bps)
        self.min_side_depth_reduce_usd = float(min_side_depth_reduce_usd)
        self.min_side_depth_halt_usd = float(min_side_depth_halt_usd)
        self.max_depth_participation_reduce = float(max_depth_participation_reduce)
        self.max_depth_participation_halt = float(max_depth_participation_halt)
        self.min_size_multiplier = max(float(min_size_multiplier), 0.01)

    def estimate_vpin(
        self,
        *,
        market_id: str,
        trades: Iterable[dict[str, Any]],
        timestamp: str | None = None,
    ) -> VPINEstimate:
        rows = list(trades)[-self.lookback_trades :]
        buy_volume = 0.0
        sell_volume = 0.0
        current_buy = 0.0
        current_sell = 0.0
        bucket_remaining = float(self.bucket_volume)
        bucket_imbalances: list[float] = []

        for row in rows:
            if not isinstance(row, dict):
                continue
            qty = _trade_qty(row)
            if qty <= 0.0:
                continue
            sign = _trade_sign(row)
            remainder = float(qty)
            while remainder > 0.0:
                take = min(bucket_remaining, remainder)
                if sign >= 0.0:
                    buy_volume += take
                    current_buy += take
                else:
                    sell_volume += take
                    current_sell += take
                bucket_remaining -= take
                remainder -= take
                if bucket_remaining <= 1e-9:
                    total = current_buy + current_sell
                    imbalance = abs(current_buy - current_sell) / max(total, 1e-9)
                    bucket_imbalances.append(float(imbalance))
                    current_buy = 0.0
                    current_sell = 0.0
                    bucket_remaining = float(self.bucket_volume)

        partial_total = current_buy + current_sell
        if partial_total > 1e-9:
            partial_imbalance = abs(current_buy - current_sell) / partial_total
            bucket_imbalances.append(float(partial_imbalance))

        total_volume = buy_volume + sell_volume
        vpin = float(mean(bucket_imbalances)) if bucket_imbalances else 0.0
        computed_at = str(timestamp or _utc_now_iso())
        return VPINEstimate(
            market_id=str(market_id).strip(),
            lookback_trades=self.lookback_trades,
            bucket_volume=float(self.bucket_volume),
            bucket_count=len(bucket_imbalances),
            mean_bucket_imbalance=vpin,
            vpin=vpin,
            buy_volume=float(buy_volume),
            sell_volume=float(sell_volume),
            total_volume=float(total_volume),
            computed_at=computed_at,
        )

    def _size_reduction_multiplier(
        self,
        *,
        vpin: float,
        spread_bps: float,
        side_depth_usd: float,
        depth_participation: float,
    ) -> float:
        factors = [1.0]
        if vpin >= self.vpin_reduce_threshold:
            span = max(self.vpin_halt_threshold - self.vpin_reduce_threshold, 1e-9)
            stress = min(max((vpin - self.vpin_reduce_threshold) / span, 0.0), 1.0)
            factors.append(1.0 - 0.9 * stress)

        if spread_bps >= self.spread_reduce_bps:
            span = max(self.spread_halt_bps - self.spread_reduce_bps, 1e-9)
            stress = min(max((spread_bps - self.spread_reduce_bps) / span, 0.0), 1.0)
            factors.append(1.0 - 0.8 * stress)

        if side_depth_usd < self.min_side_depth_reduce_usd:
            depth_ratio = side_depth_usd / max(self.min_side_depth_reduce_usd, 1e-9)
            factors.append(max(depth_ratio, self.min_size_multiplier))

        if depth_participation > self.max_depth_participation_reduce:
            participation_ratio = self.max_depth_participation_reduce / max(depth_participation, 1e-9)
            factors.append(max(participation_ratio, self.min_size_multiplier))

        return float(max(min(factors), self.min_size_multiplier))

    def evaluate(
        self,
        *,
        market_id: str,
        order_book: dict[str, Any] | None,
        reference_price: float,
        side: str,
        requested_qty: float,
        trades: Iterable[dict[str, Any]],
        queue_ahead_qty: float = 0.0,
        timestamp: str | None = None,
    ) -> QuoteSizeDecision:
        flow = self.estimate_vpin(market_id=market_id, trades=trades, timestamp=timestamp)
        micro = extract_microstructure_features(
            order_book=order_book,
            reference_price=float(reference_price),
            side=str(side),
            requested_qty=float(requested_qty),
            queue_ahead_qty=float(queue_ahead_qty),
        )
        spread_bps = float(micro.get("spread_bps", 0.0))
        side_depth_usd = float(micro.get("side_depth_usd", 0.0))
        depth_participation = float(micro.get("depth_participation", 0.0))

        halt_reasons: list[str] = []
        reduce_reasons: list[str] = []
        if flow.vpin >= self.vpin_halt_threshold:
            halt_reasons.append(
                f"vpin {flow.vpin:.3f} >= halt threshold {self.vpin_halt_threshold:.3f}"
            )
        elif flow.vpin >= self.vpin_reduce_threshold:
            reduce_reasons.append(
                f"vpin {flow.vpin:.3f} >= reduce threshold {self.vpin_reduce_threshold:.3f}"
            )

        if spread_bps >= self.spread_halt_bps:
            halt_reasons.append(
                f"spread {spread_bps:.2f}bps >= halt threshold {self.spread_halt_bps:.2f}bps"
            )
        elif spread_bps >= self.spread_reduce_bps:
            reduce_reasons.append(
                f"spread {spread_bps:.2f}bps >= reduce threshold {self.spread_reduce_bps:.2f}bps"
            )

        if side_depth_usd <= self.min_side_depth_halt_usd:
            halt_reasons.append(
                f"side depth ${side_depth_usd:.0f} <= halt floor ${self.min_side_depth_halt_usd:.0f}"
            )
        elif side_depth_usd <= self.min_side_depth_reduce_usd:
            reduce_reasons.append(
                f"side depth ${side_depth_usd:.0f} <= reduce floor ${self.min_side_depth_reduce_usd:.0f}"
            )

        if depth_participation >= self.max_depth_participation_halt:
            halt_reasons.append(
                "depth participation "
                f"{depth_participation:.3f} >= halt limit {self.max_depth_participation_halt:.3f}"
            )
        elif depth_participation >= self.max_depth_participation_reduce:
            reduce_reasons.append(
                "depth participation "
                f"{depth_participation:.3f} >= reduce limit {self.max_depth_participation_reduce:.3f}"
            )

        decision_ts = str(timestamp or _utc_now_iso())
        if halt_reasons:
            decision = QuoteSizeDecision(
                market_id=str(market_id).strip(),
                action="halt_quotes",
                severity="critical",
                quote_enabled=False,
                size_multiplier=0.0,
                reason="; ".join(halt_reasons),
                metrics={
                    "vpin": float(flow.vpin),
                    "spread_bps": spread_bps,
                    "side_depth_usd": side_depth_usd,
                    "depth_participation": depth_participation,
                },
                timestamp=decision_ts,
            )
        elif reduce_reasons:
            multiplier = self._size_reduction_multiplier(
                vpin=float(flow.vpin),
                spread_bps=spread_bps,
                side_depth_usd=side_depth_usd,
                depth_participation=depth_participation,
            )
            decision = QuoteSizeDecision(
                market_id=str(market_id).strip(),
                action="reduce_size",
                severity="warning",
                quote_enabled=True,
                size_multiplier=multiplier,
                reason="; ".join(reduce_reasons),
                metrics={
                    "vpin": float(flow.vpin),
                    "spread_bps": spread_bps,
                    "side_depth_usd": side_depth_usd,
                    "depth_participation": depth_participation,
                },
                timestamp=decision_ts,
            )
        else:
            decision = QuoteSizeDecision(
                market_id=str(market_id).strip(),
                action="allow",
                severity="normal",
                quote_enabled=True,
                size_multiplier=1.0,
                reason="flow/liquidity within thresholds",
                metrics={
                    "vpin": float(flow.vpin),
                    "spread_bps": spread_bps,
                    "side_depth_usd": side_depth_usd,
                    "depth_participation": depth_participation,
                },
                timestamp=decision_ts,
            )

        if self._store is not None:
            self._store.append(
                category="informed_flow_quote_size_decisions",
                payload={
                    "decision": decision.to_dict(),
                    "flow": flow.to_dict(),
                    "microstructure": dict(micro),
                },
                timestamp=decision_ts,
            )
        return decision

    def replay_decisions(self, *, market_id: str | None = None) -> list[QuoteSizeDecision]:
        if self._store is None:
            return []
        rows = self._store.read(category="informed_flow_quote_size_decisions", limit=100000)
        out: list[QuoteSizeDecision] = []
        for row in reversed(rows):
            decision_payload = dict(row.payload).get("decision", {})
            if not isinstance(decision_payload, dict):
                continue
            if market_id is not None and str(decision_payload.get("market_id")) != str(market_id):
                continue
            out.append(QuoteSizeDecision(**decision_payload))
        return out
