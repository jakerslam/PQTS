"""Short-cycle binary strategy primitives for scan, execution safety, and governance."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from statistics import fmean
from typing import Iterable, Mapping


@dataclass(frozen=True)
class ShortCycleQuote:
    market_id: str
    asset: str
    interval: str
    ask_yes: float
    ask_no: float
    yes_depth: float
    no_depth: float
    timestamp_ms: int
    fee_buffer: float = 0.0
    slippage_buffer: float = 0.0


@dataclass(frozen=True)
class BundleSignal:
    market_id: str
    asset: str
    interval: str
    bundle_edge: float
    timestamp_ms: int


@dataclass(frozen=True)
class ShortCycleConfig:
    min_bundle_edge: float = 0.001
    min_depth: float = 100.0
    stale_limit_ms: int = 1_000
    single_leg_enabled: bool = False
    min_single_leg_edge: float = 0.01
    edge_floor_for_disable: float = -0.001
    max_orders_per_minute: int = 120
    max_trades_per_day: int = 5_000
    enabled_assets: tuple[str, ...] = ("BTC",)
    enabled_intervals: tuple[str, ...] = ("5m", "15m")


@dataclass(frozen=True)
class SecurityHealth:
    private_control_plane: bool
    operator_allowlist_enabled: bool
    command_allowlist_enabled: bool
    sandbox_isolation_enabled: bool
    least_privilege_scopes: bool


@dataclass
class ThroughputCounters:
    detected: int = 0
    executed: int = 0
    rejected: int = 0
    realized_edges: deque[float] = field(default_factory=deque)

    def record(self, *, executed: bool, realized_edge: float = 0.0, rejected: bool = False, limit: int = 500) -> None:
        self.detected += 1
        if executed:
            self.executed += 1
            self.realized_edges.append(float(realized_edge))
            while len(self.realized_edges) > limit:
                self.realized_edges.popleft()
        if rejected:
            self.rejected += 1


def classify_external_claim(claim_reproducible: bool, claim_has_direct_evidence: bool) -> str:
    if claim_reproducible and claim_has_direct_evidence:
        return "observed"
    if claim_has_direct_evidence:
        return "inferred"
    return "unverified"


class ShortCycleBinaryEngine:
    """Scanner/guardrail surface for short-cycle binary and HFT-adjacent workflows."""

    def __init__(self, config: ShortCycleConfig | None = None) -> None:
        self.config = config or ShortCycleConfig()
        self.disabled_buckets: set[tuple[str, str]] = set()
        self.allowed_expansion_assets: set[str] = set(self.config.enabled_assets)
        self.counters = ThroughputCounters()
        self.order_ts_ms: deque[int] = deque()
        self.trade_ts_ms: deque[int] = deque()

    def disable_bucket(self, asset: str, interval: str) -> None:
        self.disabled_buckets.add((asset.upper(), interval))

    def enable_bucket(self, asset: str, interval: str) -> None:
        self.disabled_buckets.discard((asset.upper(), interval))

    def _bucket_enabled(self, asset: str, interval: str) -> bool:
        asset = asset.upper()
        return (
            asset in {item.upper() for item in self.config.enabled_assets}
            and interval in set(self.config.enabled_intervals)
            and (asset, interval) not in self.disabled_buckets
        )

    @staticmethod
    def bundle_edge(quote: ShortCycleQuote) -> float:
        return 1.0 - (float(quote.ask_yes) + float(quote.ask_no)) - float(quote.fee_buffer) - float(quote.slippage_buffer)

    def scan_bundle(self, quotes: Iterable[ShortCycleQuote], *, now_ms: int) -> list[BundleSignal]:
        signals: list[BundleSignal] = []
        for quote in quotes:
            if not self._bucket_enabled(quote.asset, quote.interval):
                continue
            if now_ms - int(quote.timestamp_ms) > self.config.stale_limit_ms:
                continue
            if min(float(quote.yes_depth), float(quote.no_depth)) < self.config.min_depth:
                continue
            edge = self.bundle_edge(quote)
            if edge < self.config.min_bundle_edge:
                continue
            signals.append(
                BundleSignal(
                    market_id=quote.market_id,
                    asset=quote.asset.upper(),
                    interval=quote.interval,
                    bundle_edge=edge,
                    timestamp_ms=quote.timestamp_ms,
                )
            )
        return signals

    @staticmethod
    def validate_legging(
        *,
        execution_window_ms: int,
        max_legging_ms: int,
        unhedged_notional: float,
        max_unhedged_notional: float,
    ) -> tuple[bool, str]:
        if execution_window_ms > max_legging_ms:
            return False, "legging_time_exceeded"
        if unhedged_notional > max_unhedged_notional:
            return False, "unhedged_notional_exceeded"
        return True, "ok"

    def evaluate_single_leg_mode(self, *, edge: float, all_existing_gates_pass: bool) -> tuple[bool, str]:
        if not self.config.single_leg_enabled:
            return False, "single_leg_disabled"
        if not all_existing_gates_pass:
            return False, "risk_gate_failed"
        if edge < self.config.min_single_leg_edge:
            return False, "edge_below_single_leg_threshold"
        return True, "ok"

    def record_outcome(self, *, executed: bool, realized_edge: float = 0.0, rejected: bool = False) -> None:
        self.counters.record(executed=executed, realized_edge=realized_edge, rejected=rejected)

    def metrics(self) -> dict[str, float]:
        detected = max(self.counters.detected, 1)
        executed = self.counters.executed
        rejected = self.counters.rejected
        realized_edges = list(self.counters.realized_edges)
        fill_rate = executed / detected
        reject_rate = rejected / detected
        realized_edge_per_trade = fmean(realized_edges) if realized_edges else 0.0
        cumulative_net_alpha = float(sum(realized_edges))
        return {
            "opportunities_detected": float(self.counters.detected),
            "opportunities_executed": float(executed),
            "fill_rate": float(fill_rate),
            "reject_rate": float(reject_rate),
            "realized_edge_per_trade": float(realized_edge_per_trade),
            "cumulative_net_alpha": cumulative_net_alpha,
        }

    def should_disable(self) -> bool:
        metrics = self.metrics()
        return metrics["realized_edge_per_trade"] < self.config.edge_floor_for_disable

    def security_health_passed(self, health: SecurityHealth) -> tuple[bool, str]:
        if not health.private_control_plane:
            return False, "public_admin_ingress_disallowed"
        if not health.operator_allowlist_enabled:
            return False, "operator_allowlist_required"
        if not health.command_allowlist_enabled:
            return False, "command_allowlist_required"
        if not health.sandbox_isolation_enabled:
            return False, "sandbox_isolation_required"
        if not health.least_privilege_scopes:
            return False, "least_privilege_required"
        return True, "ok"

    def record_order_activity(self, *, timestamp_ms: int, trade_executed: bool = False) -> None:
        self.order_ts_ms.append(timestamp_ms)
        if trade_executed:
            self.trade_ts_ms.append(timestamp_ms)
        self._gc_activity(now_ms=timestamp_ms)

    def _gc_activity(self, *, now_ms: int) -> None:
        one_min_ago = now_ms - 60_000
        while self.order_ts_ms and self.order_ts_ms[0] < one_min_ago:
            self.order_ts_ms.popleft()
        day_ago = now_ms - 86_400_000
        while self.trade_ts_ms and self.trade_ts_ms[0] < day_ago:
            self.trade_ts_ms.popleft()

    def frequency_governance(self, *, now_ms: int) -> tuple[bool, str]:
        self._gc_activity(now_ms=now_ms)
        if len(self.order_ts_ms) > self.config.max_orders_per_minute:
            return False, "orders_per_minute_exceeded"
        if len(self.trade_ts_ms) > self.config.max_trades_per_day:
            return False, "trades_per_day_exceeded"
        return True, "ok"

    @staticmethod
    def kelly_constrained_fraction(
        *,
        win_probability: float,
        payout_multiple: float,
        kelly_fraction_cap: float,
        hard_risk_cap: float,
    ) -> dict[str, float]:
        b = max(float(payout_multiple), 0.0001)
        p = max(min(float(win_probability), 1.0), 0.0)
        q = 1.0 - p
        full_kelly = max(((b * p) - q) / b, 0.0)
        requested = min(full_kelly, float(kelly_fraction_cap))
        approved = min(requested, float(hard_risk_cap))
        return {
            "full_kelly_fraction": full_kelly,
            "requested_fraction": requested,
            "approved_fraction": approved,
        }

    def can_expand_asset(self, *, asset: str, readiness_checks: Mapping[str, bool]) -> tuple[bool, str]:
        asset_upper = asset.upper()
        if asset_upper not in self.allowed_expansion_assets:
            return False, "asset_not_allowlisted"
        missing = sorted(key for key, value in readiness_checks.items() if not value)
        if missing:
            return False, f"readiness_failed:{','.join(missing)}"
        return True, "ok"

    @staticmethod
    def validate_exogenous_feed(
        *,
        source_quality: str,
        sample_timestamp_ms: int,
        now_ms: int,
        max_age_ms: int,
    ) -> tuple[bool, str]:
        if source_quality.lower() not in {"observed", "inferred"}:
            return False, "source_quality_invalid"
        if now_ms - sample_timestamp_ms > max_age_ms:
            return False, "exogenous_feed_stale"
        return True, "ok"
