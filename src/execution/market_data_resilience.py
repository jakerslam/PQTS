"""Market-data resilience controls: gap replay + stale-feed failover."""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from statistics import median
from typing import Any, Deque, Dict, List, Mapping, Optional, Tuple

from core.hotpath_runtime import quote_state


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value: Any, *, fallback: datetime) -> datetime:
    token = str(value or "").strip()
    if not token:
        return fallback
    dt = datetime.fromisoformat(token.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class MarketDataResiliencePolicy:
    enabled: bool = True
    stale_after_seconds: float = 5.0
    replay_window_seconds: float = 120.0
    backup_venues_by_venue: Dict[str, List[str]] = field(default_factory=dict)
    backup_venues_by_market: Dict[str, List[str]] = field(default_factory=dict)
    allow_synthetic_fallback: bool = True
    min_price_by_symbol: Dict[str, float] = field(default_factory=dict)
    max_price_by_symbol: Dict[str, float] = field(default_factory=dict)
    max_price_deviation_bps: float = 0.0
    max_mid_deviation_bps: float = 0.0
    max_spread_bps: float = 0.0
    rolling_window_size: int = 0
    min_rolling_samples: int = 0
    max_rolling_price_deviation_bps: float = 0.0


@dataclass(frozen=True)
class QuoteResolution:
    mode: str
    source_venue: str
    stale: bool
    gap: bool
    replay_age_seconds: float
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MarketDataResilienceManager:
    """Resolve quote gaps and stale feeds using deterministic fallback ordering."""

    def __init__(self, policy: MarketDataResiliencePolicy | None = None):
        self.policy = policy or MarketDataResiliencePolicy()
        self._last_good: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._price_history: Dict[Tuple[str, str], Deque[float]] = {}
        self._metrics = {
            "live_quotes": 0,
            "stale_quotes": 0,
            "gap_quotes": 0,
            "failover_quotes": 0,
            "replay_quotes": 0,
            "synthetic_quotes": 0,
            "unresolved_quotes": 0,
            "sanity_reject_quotes": 0,
        }

    def _quote_state(self, quote: Mapping[str, Any], *, now: datetime) -> tuple[bool, bool]:
        try:
            price = float(quote.get("price", 0.0) or 0.0)
        except (TypeError, ValueError):
            return False, False
        ts = _parse_ts(quote.get("timestamp"), fallback=now)
        age_seconds = max((now - ts).total_seconds(), 0.0)
        stale, usable = quote_state(
            price=float(price),
            age_seconds=float(age_seconds),
            stale_after_seconds=float(self.policy.stale_after_seconds),
        )
        return bool(stale), bool(usable)

    @staticmethod
    def _symbol_lookup(mapping: Mapping[str, float], symbol: str) -> Optional[float]:
        if not mapping:
            return None
        token = str(symbol)
        candidates = [
            token,
            token.upper(),
            token.replace("-", "").upper(),
            token.replace("_", "").upper(),
        ]
        for key in candidates:
            if key in mapping:
                try:
                    return float(mapping[key])
                except (TypeError, ValueError):
                    return None
        return None

    @staticmethod
    def _quote_price(quote: Mapping[str, Any]) -> Optional[float]:
        try:
            return float(quote.get("price", 0.0) or 0.0)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _best_bid_ask(quote: Mapping[str, Any]) -> tuple[Optional[float], Optional[float]]:
        bid = quote.get("bid")
        ask = quote.get("ask")
        if bid is not None and ask is not None:
            try:
                parsed_bid = float(bid)
                parsed_ask = float(ask)
                if parsed_bid > 0.0 and parsed_ask > 0.0:
                    return parsed_bid, parsed_ask
            except (TypeError, ValueError):
                pass

        order_book = quote.get("order_book")
        if not isinstance(order_book, Mapping):
            return None, None

        bids = order_book.get("bids") or []
        asks = order_book.get("asks") or []
        if not bids or not asks:
            return None, None

        try:
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
        except (IndexError, TypeError, ValueError):
            return None, None
        return best_bid, best_ask

    def _rolling_price_reason(self, *, venue: str, symbol: str, price: float) -> str:
        max_deviation_bps = float(self.policy.max_rolling_price_deviation_bps or 0.0)
        if max_deviation_bps <= 0.0:
            return ""

        samples = self._price_history.get((str(venue), str(symbol)))
        if not samples:
            return ""

        min_samples = max(int(self.policy.min_rolling_samples or 0), 1)
        if len(samples) < min_samples:
            return ""

        anchor = float(median(samples))
        if anchor <= 0.0:
            return ""

        deviation_bps = abs(price - anchor) / anchor * 10000.0
        if deviation_bps > max_deviation_bps:
            return f"rolling_price_deviation_bps:{deviation_bps:.4f}>{max_deviation_bps:.4f}"
        return ""

    def _price_sanity_reason(
        self,
        quote: Optional[Mapping[str, Any]],
        *,
        venue: str,
        symbol: str,
    ) -> str:
        if quote is None:
            return "missing_quote"

        price = self._quote_price(quote)
        if price is None or price <= 0.0:
            return "non_positive_price"

        min_price = self._symbol_lookup(self.policy.min_price_by_symbol, symbol)
        if min_price is not None and price < min_price:
            return f"price_below_min:{price:.8g}<{min_price:.8g}"

        max_price = self._symbol_lookup(self.policy.max_price_by_symbol, symbol)
        if max_price is not None and price > max_price:
            return f"price_above_max:{price:.8g}>{max_price:.8g}"

        bid, ask = self._best_bid_ask(quote)
        if bid is not None and ask is not None:
            if bid <= 0.0 or ask <= 0.0 or ask < bid:
                return "invalid_bid_ask"
            mid = (bid + ask) / 2.0
            spread_bps = abs(ask - bid) / max(mid, 1e-12) * 10000.0
            max_spread_bps = float(self.policy.max_spread_bps or 0.0)
            if max_spread_bps > 0.0 and spread_bps > max_spread_bps:
                return f"spread_bps:{spread_bps:.4f}>{max_spread_bps:.4f}"

            max_mid_deviation_bps = float(self.policy.max_mid_deviation_bps or 0.0)
            if max_mid_deviation_bps > 0.0:
                mid_deviation_bps = abs(price - mid) / max(mid, 1e-12) * 10000.0
                if mid_deviation_bps > max_mid_deviation_bps:
                    return (
                        f"mid_deviation_bps:{mid_deviation_bps:.4f}>"
                        f"{max_mid_deviation_bps:.4f}"
                    )

        max_deviation_bps = float(self.policy.max_price_deviation_bps or 0.0)
        if max_deviation_bps > 0.0:
            last_good = self._last_good.get((str(venue), str(symbol)))
            if last_good:
                last_price = self._quote_price(last_good)
                if last_price is not None and last_price > 0.0:
                    deviation_bps = abs(price - last_price) / last_price * 10000.0
                    if deviation_bps > max_deviation_bps:
                        return f"price_deviation_bps:{deviation_bps:.4f}>{max_deviation_bps:.4f}"

        return self._rolling_price_reason(venue=venue, symbol=symbol, price=float(price))

    def _is_stale(self, quote: Mapping[str, Any], *, now: datetime) -> bool:
        stale, _usable = self._quote_state(quote, now=now)
        return bool(stale)

    def _is_usable(
        self,
        quote: Optional[Mapping[str, Any]],
        *,
        now: datetime,
        venue: str,
        symbol: str,
    ) -> bool:
        if quote is None:
            return False
        if self._price_sanity_reason(quote, venue=venue, symbol=symbol):
            return False
        _stale, usable = self._quote_state(quote, now=now)
        return bool(usable)

    @staticmethod
    def _copy_quote(quote: Mapping[str, Any]) -> Dict[str, Any]:
        out = dict(quote)
        if "order_book" in quote and isinstance(quote.get("order_book"), Mapping):
            out["order_book"] = dict(quote["order_book"])
        return out

    def _record_live(self, *, venue: str, symbol: str, quote: Mapping[str, Any]) -> None:
        self._last_good[(str(venue), str(symbol))] = self._copy_quote(quote)
        price = self._quote_price(quote)
        if price is None or price <= 0.0:
            return
        maxlen = int(self.policy.rolling_window_size or 0)
        if maxlen <= 0:
            return
        key = (str(venue), str(symbol))
        samples = self._price_history.get(key)
        if samples is None or samples.maxlen != maxlen:
            existing = list(samples or [])[-maxlen:]
            samples = deque(existing, maxlen=maxlen)
            self._price_history[key] = samples
        samples.append(float(price))

    def _candidate_backups(self, *, venue: str, market: str) -> List[str]:
        candidates: List[str] = []
        for key in (
            str(venue),
            str(venue).lower(),
        ):
            for backup in self.policy.backup_venues_by_venue.get(key, []):
                if backup not in candidates:
                    candidates.append(str(backup))
        for key in (
            str(market),
            str(market).lower(),
        ):
            for backup in self.policy.backup_venues_by_market.get(key, []):
                if backup not in candidates:
                    candidates.append(str(backup))
        return [name for name in candidates if name != str(venue)]

    def resolve(
        self,
        *,
        venue: str,
        symbol: str,
        market: str,
        live_quote: Optional[Dict[str, Any]],
        raw_quotes: Mapping[Tuple[str, str], Optional[Dict[str, Any]]],
        now: Optional[datetime] = None,
    ) -> Tuple[Optional[Dict[str, Any]], QuoteResolution]:
        now_dt = now or _utc_now()
        if not bool(self.policy.enabled):
            if live_quote is None:
                return None, QuoteResolution(
                    mode="disabled_no_quote",
                    source_venue=str(venue),
                    stale=False,
                    gap=True,
                    replay_age_seconds=0.0,
                    reason="missing_quote",
                )
            self._record_live(venue=venue, symbol=symbol, quote=live_quote)
            return self._copy_quote(live_quote), QuoteResolution(
                mode="disabled_live",
                source_venue=str(venue),
                stale=False,
                gap=False,
                replay_age_seconds=0.0,
            )

        stale = bool(live_quote is not None and self._is_stale(live_quote, now=now_dt))
        gap = live_quote is None
        if live_quote is not None:
            self._metrics["live_quotes"] = int(self._metrics["live_quotes"]) + 1
            if stale:
                self._metrics["stale_quotes"] = int(self._metrics["stale_quotes"]) + 1
        else:
            self._metrics["gap_quotes"] = int(self._metrics["gap_quotes"]) + 1

        live_sanity_reason = self._price_sanity_reason(
            live_quote,
            venue=venue,
            symbol=symbol,
        )
        if live_sanity_reason and live_quote is not None:
            self._metrics["sanity_reject_quotes"] = (
                int(self._metrics["sanity_reject_quotes"]) + 1
            )

        if self._is_usable(live_quote, now=now_dt, venue=venue, symbol=symbol):
            self._record_live(venue=venue, symbol=symbol, quote=live_quote or {})
            return self._copy_quote(live_quote or {}), QuoteResolution(
                mode="live",
                source_venue=str(venue),
                stale=False,
                gap=False,
                replay_age_seconds=0.0,
            )

        for backup in self._candidate_backups(venue=venue, market=market):
            backup_quote = raw_quotes.get((str(backup), str(symbol)))
            if not self._is_usable(
                backup_quote,
                now=now_dt,
                venue=str(backup),
                symbol=symbol,
            ):
                continue
            quote = self._copy_quote(backup_quote or {})
            quote["source_venue"] = str(backup)
            quote["failover_from_venue"] = str(venue)
            self._record_live(venue=venue, symbol=symbol, quote=quote)
            self._metrics["failover_quotes"] = int(self._metrics["failover_quotes"]) + 1
            return quote, QuoteResolution(
                mode="failover",
                source_venue=str(backup),
                stale=stale,
                gap=gap,
                replay_age_seconds=0.0,
                reason="primary_stale_or_gap",
            )

        replay = self._last_good.get((str(venue), str(symbol)))
        if replay is not None:
            replay_ts = _parse_ts(replay.get("timestamp"), fallback=now_dt)
            replay_age = max((now_dt - replay_ts).total_seconds(), 0.0)
            if replay_age <= float(self.policy.replay_window_seconds):
                quote = self._copy_quote(replay)
                quote["replayed"] = True
                self._metrics["replay_quotes"] = int(self._metrics["replay_quotes"]) + 1
                return quote, QuoteResolution(
                    mode="replay",
                    source_venue=str(venue),
                    stale=stale,
                    gap=gap,
                    replay_age_seconds=float(replay_age),
                    reason="recent_last_good",
                )

        self._metrics["unresolved_quotes"] = int(self._metrics["unresolved_quotes"]) + 1
        return None, QuoteResolution(
            mode="unresolved",
            source_venue=str(venue),
            stale=stale,
            gap=gap,
            replay_age_seconds=0.0,
            reason=live_sanity_reason or ("gap" if gap else "unusable_quote"),
        )

    def snapshot_metrics(self) -> Dict[str, Any]:
        return {
            "policy": asdict(self.policy),
            "metrics": {key: int(value) for key, value in self._metrics.items()},
        }

    def record_synthetic_quote(self) -> None:
        self._metrics["synthetic_quotes"] = int(self._metrics["synthetic_quotes"]) + 1
