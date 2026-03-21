"""Strategy-family governance contracts (RVX, PWX, KRL, SOLS)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from core.compaction_primitives import parse_utc_iso as _parse_iso


@dataclass(frozen=True)
class NearEvenMarketCandidate:
    market_id: str
    price: float
    fee_adjusted_spread_bps: float
    resting_depth: float
    event_start_ts: str
    quote_staleness_ms: int


@dataclass(frozen=True)
class NearEvenMarketSelection:
    market_id: str
    eligible: bool
    rank_score: float
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class PassiveFillDecision:
    compliant: bool
    reason_code: str


@dataclass(frozen=True)
class MicroLadderState:
    outstanding_by_level: dict[str, float]
    filled_by_level: dict[str, float]
    canceled_by_level: dict[str, float]
    net_inventory: float
    rebalance_actions: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "outstanding_by_level": dict(self.outstanding_by_level),
            "filled_by_level": dict(self.filled_by_level),
            "canceled_by_level": dict(self.canceled_by_level),
            "net_inventory": float(self.net_inventory),
            "rebalance_actions": list(self.rebalance_actions),
        }


@dataclass(frozen=True)
class MicroEdgeExitDecision:
    action: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class CopyabilityLabelDecision:
    label: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class BlackoutDecision:
    action: str
    in_blackout: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ForecastOnlyPurityDecision:
    allow_trade: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ForecastSource:
    source_id: str
    tier: str
    freshness_ms: int
    confidence: float


@dataclass(frozen=True)
class ForecastSourceTierDecision:
    selected_source_id: str | None
    action: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class MarketClassEligibilityDecision:
    allow_class: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class MarketClassEdgeConcentration:
    scoped_to_class: str | None
    broad_coverage_allowed: bool
    concentration_ratio: float


@dataclass(frozen=True)
class AdvisoryDecomposition:
    source_contributions: dict[str, float]
    target_contract: str
    proxy_venue: str
    freshness_ms: int
    read_only: bool


@dataclass(frozen=True)
class TimeframeSignal:
    timeframe: str
    directional_bias: str
    confidence: float
    freshness_ms: int


@dataclass(frozen=True)
class MultiTimeframeConflictDecision:
    conflict: bool
    unified_confidence: float
    reason_codes: tuple[str, ...]


def select_near_even_markets(
    *,
    candidates: list[NearEvenMarketCandidate],
    band_low: float = 0.47,
    band_high: float = 0.52,
    min_depth: float = 500.0,
    min_spread_bps: float = 2.0,
    max_quote_staleness_ms: int = 2_000,
) -> list[NearEvenMarketSelection]:
    """Scan near-even contracts and mark ineligible markets with reason codes."""

    out: list[NearEvenMarketSelection] = []
    now = datetime.now(timezone.utc)
    for row in candidates:
        reasons: list[str] = []
        if not (float(band_low) <= float(row.price) <= float(band_high)):
            reasons.append("outside_near_even_band")
        if float(row.resting_depth) < float(min_depth):
            reasons.append("insufficient_depth")
        if float(row.fee_adjusted_spread_bps) < float(min_spread_bps):
            reasons.append("spread_below_threshold")
        if int(row.quote_staleness_ms) > int(max_quote_staleness_ms):
            reasons.append("quote_stale")
        horizon_minutes = (_parse_iso(row.event_start_ts) - now).total_seconds() / 60.0
        rank = (
            float(row.fee_adjusted_spread_bps)
            + min(float(row.resting_depth) / 1_000.0, 5.0)
            + max(horizon_minutes / 120.0, 0.0)
            - (float(row.quote_staleness_ms) / 10_000.0)
        )
        out.append(
            NearEvenMarketSelection(
                market_id=row.market_id,
                eligible=not bool(reasons),
                rank_score=rank,
                reason_codes=tuple(sorted(set(reasons))),
            )
        )
    return sorted(out, key=lambda row: row.rank_score, reverse=True)


def evaluate_passive_only_fill(
    *,
    passive_fill: bool,
    policy_override_enabled: bool,
) -> PassiveFillDecision:
    if passive_fill:
        return PassiveFillDecision(compliant=True, reason_code="passive_fill")
    if policy_override_enabled:
        return PassiveFillDecision(compliant=False, reason_code="aggressive_fill_policy_override")
    return PassiveFillDecision(compliant=False, reason_code="aggressive_fill_policy_violation")


def update_micro_lot_ladder(
    *,
    state: MicroLadderState,
    level: str,
    filled_qty: float,
    side: str,
    per_side_inventory_cap: float,
) -> MicroLadderState:
    """Update ladder state and enforce bounded directional inventory caps."""

    token_level = str(level).strip()
    sign = 1.0 if str(side).strip().upper() == "BUY" else -1.0
    new_inventory = float(state.net_inventory) + (sign * float(filled_qty))
    actions: list[str] = list(state.rebalance_actions)
    if abs(new_inventory) > float(per_side_inventory_cap):
        actions.append("inventory_cap_rebalance")
        new_inventory = float(per_side_inventory_cap) * (1.0 if new_inventory > 0 else -1.0)
    filled = dict(state.filled_by_level)
    filled[token_level] = float(filled.get(token_level, 0.0)) + float(filled_qty)
    return MicroLadderState(
        outstanding_by_level=dict(state.outstanding_by_level),
        filled_by_level=filled,
        canceled_by_level=dict(state.canceled_by_level),
        net_inventory=new_inventory,
        rebalance_actions=tuple(actions),
    )


def evaluate_micro_edge_exit(
    *,
    expected_edge_bps: float,
    tick_target_hit: bool,
    mean_reversion_hit: bool,
    max_hold_timeout_hit: bool,
    time_to_event_seconds: int,
    edge_decay_threshold_bps: float,
) -> MicroEdgeExitDecision:
    """Emit explicit reduce/flatten actions as edge decays or timeout approaches."""

    reasons: list[str] = []
    if tick_target_hit:
        reasons.append("tick_target_exit")
        return MicroEdgeExitDecision(action="reduce", reason_codes=tuple(reasons))
    if mean_reversion_hit:
        reasons.append("mean_reversion_exit")
        return MicroEdgeExitDecision(action="reduce", reason_codes=tuple(reasons))
    if max_hold_timeout_hit or int(time_to_event_seconds) < 600:
        reasons.append("timeout_or_event_near")
        return MicroEdgeExitDecision(action="flatten", reason_codes=tuple(reasons))
    if float(expected_edge_bps) < float(edge_decay_threshold_bps):
        reasons.append("edge_decay_below_threshold")
        return MicroEdgeExitDecision(action="reduce", reason_codes=tuple(reasons))
    return MicroEdgeExitDecision(action="hold", reason_codes=())


def classify_copyability_label(
    *,
    latency_sensitive: bool,
    queue_position_sensitive: bool,
    fill_decay_half_life_seconds: int,
) -> CopyabilityLabelDecision:
    reasons: list[str] = []
    if latency_sensitive and queue_position_sensitive and int(fill_decay_half_life_seconds) <= 10:
        reasons.append("latency_queue_sensitive")
        return CopyabilityLabelDecision(label="non_copyable", reason_codes=tuple(reasons))
    if latency_sensitive or int(fill_decay_half_life_seconds) <= 30:
        reasons.append("delay_sensitive")
        return CopyabilityLabelDecision(label="delayed_signal_only", reason_codes=tuple(reasons))
    return CopyabilityLabelDecision(label="copy_safe", reason_codes=())


def evaluate_event_time_blackout(
    *,
    now_ts: str,
    event_start_ts: str,
    settlement_ts: str,
    inventory_open: bool,
    pre_start_blackout_minutes: int,
    in_play_blackout_enabled: bool,
    settlement_blackout_minutes: int,
    hedging_active: bool,
    explicit_reapproval: bool,
) -> BlackoutDecision:
    """Enforce blackout windows and flatten/reapprove open inventory."""

    now = _parse_iso(now_ts)
    start = _parse_iso(event_start_ts)
    settlement = _parse_iso(settlement_ts)
    pre_start = start - timedelta(minutes=max(int(pre_start_blackout_minutes), 0))
    pre_settle = settlement - timedelta(minutes=max(int(settlement_blackout_minutes), 0))
    in_blackout = bool((now >= pre_start) or (now >= start and in_play_blackout_enabled) or (now >= pre_settle))
    if not in_blackout:
        return BlackoutDecision(action="allow", in_blackout=False, reason_codes=())
    reasons = ["event_time_blackout_active"]
    if inventory_open and not hedging_active and not explicit_reapproval:
        return BlackoutDecision(action="flatten", in_blackout=True, reason_codes=tuple(reasons))
    if inventory_open and explicit_reapproval:
        reasons.append("inventory_reapproved")
        return BlackoutDecision(action="allow_reapproved", in_blackout=True, reason_codes=tuple(reasons))
    return BlackoutDecision(action="hold", in_blackout=True, reason_codes=tuple(reasons))


def enforce_forecast_only_signal_purity(
    *,
    forecast_only: bool,
    input_classes: list[str],
    allowed_forecast_inputs: set[str],
    explicit_override: bool = False,
) -> ForecastOnlyPurityDecision:
    """Fail closed when forecast-only strategies receive disallowed input classes."""

    if not forecast_only:
        return ForecastOnlyPurityDecision(allow_trade=True, reason_codes=())
    disallowed = sorted(
        {
            str(item).strip().lower()
            for item in input_classes
            if str(item).strip().lower() not in {x.lower() for x in allowed_forecast_inputs}
        }
    )
    if disallowed and not explicit_override:
        return ForecastOnlyPurityDecision(
            allow_trade=False,
            reason_codes=("forecast_only_policy_violation",),
        )
    return ForecastOnlyPurityDecision(allow_trade=True, reason_codes=())


def choose_forecast_source_tier(
    *,
    sources: list[ForecastSource],
    require_direct_model_edge: bool,
    allow_low_tier_as_sole_input: bool = False,
) -> ForecastSourceTierDecision:
    """Prefer authoritative tiers and block low-tier-only inputs when required."""

    tier_rank = {"direct_model": 3, "normalized_api": 2, "consumer_summary": 1}
    ranked = sorted(
        sources,
        key=lambda row: (tier_rank.get(str(row.tier).strip().lower(), 0), float(row.confidence)),
        reverse=True,
    )
    if not ranked:
        return ForecastSourceTierDecision(None, "block", ("no_forecast_source_available",))
    best = ranked[0]
    if require_direct_model_edge and str(best.tier).strip().lower() != "direct_model":
        if allow_low_tier_as_sole_input:
            return ForecastSourceTierDecision(best.source_id, "allow_audited_override", ("lower_tier_source_override",))
        return ForecastSourceTierDecision(None, "block", ("requires_direct_model_tier",))
    return ForecastSourceTierDecision(best.source_id, "allow", ())


def evaluate_market_class_fit(
    *,
    declared_market_classes: set[str],
    target_market_class: str,
    has_class_priors: bool,
    has_class_calibration: bool,
    has_exec_quality_evidence: bool,
) -> MarketClassEligibilityDecision:
    reasons: list[str] = []
    token = str(target_market_class).strip().lower()
    if token not in {x.lower() for x in declared_market_classes}:
        reasons.append("undeclared_market_class")
    if not has_class_priors:
        reasons.append("missing_class_priors")
    if not has_class_calibration:
        reasons.append("missing_class_calibration")
    if not has_exec_quality_evidence:
        reasons.append("missing_class_execution_evidence")
    return MarketClassEligibilityDecision(allow_class=not bool(reasons), reason_codes=tuple(sorted(set(reasons))))


def compute_market_class_edge_concentration(
    metrics_by_class: dict[str, dict[str, float]],
    *,
    concentration_threshold: float = 0.65,
) -> MarketClassEdgeConcentration:
    """Scope deployment claims when edge is concentrated in one class."""

    if not metrics_by_class:
        return MarketClassEdgeConcentration(None, False, 1.0)
    by_alpha = {
        str(k): float(v.get("net_alpha", 0.0))
        for k, v in metrics_by_class.items()
    }
    total = sum(max(x, 0.0) for x in by_alpha.values())
    if total <= 0.0:
        return MarketClassEdgeConcentration(None, False, 1.0)
    top_class, top_alpha = max(by_alpha.items(), key=lambda row: row[1])
    ratio = max(top_alpha, 0.0) / total
    return MarketClassEdgeConcentration(
        scoped_to_class=(top_class if ratio >= float(concentration_threshold) else None),
        broad_coverage_allowed=ratio < float(concentration_threshold),
        concentration_ratio=ratio,
    )


def build_proxy_contract_advisory_decomposition(
    *,
    target_contract: str,
    proxy_venue: str,
    proxy_flow_weight: float,
    target_market_weight: float,
    technical_weight: float,
    freshness_ms: int,
) -> AdvisoryDecomposition:
    weights = {
        "proxy_flow": max(float(proxy_flow_weight), 0.0),
        "target_market": max(float(target_market_weight), 0.0),
        "technical_context": max(float(technical_weight), 0.0),
    }
    total = sum(weights.values()) or 1.0
    normalized = {k: v / total for k, v in weights.items()}
    return AdvisoryDecomposition(
        source_contributions=normalized,
        target_contract=str(target_contract).strip(),
        proxy_venue=str(proxy_venue).strip(),
        freshness_ms=int(max(freshness_ms, 0)),
        read_only=True,
    )


def evaluate_multitimeframe_conflict(
    *,
    signals: list[TimeframeSignal],
    conflict_threshold: float = 0.35,
) -> MultiTimeframeConflictDecision:
    if not signals:
        raise ValueError("signals are required")
    up = sum(float(row.confidence) for row in signals if str(row.directional_bias).lower() in {"up", "bull"})
    down = sum(float(row.confidence) for row in signals if str(row.directional_bias).lower() in {"down", "bear"})
    total = up + down
    if total <= 0.0:
        return MultiTimeframeConflictDecision(True, 0.0, ("no_directional_confidence",))
    imbalance = abs(up - down) / total
    conflict = imbalance < float(conflict_threshold)
    unified = 0.0 if conflict else max(up, down) / total
    reasons = ("cross_timeframe_conflict",) if conflict else ()
    return MultiTimeframeConflictDecision(conflict=conflict, unified_confidence=unified, reason_codes=reasons)
