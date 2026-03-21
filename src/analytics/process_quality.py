"""Process-discipline and capital-efficiency analytics contracts."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any

from core.compaction_primitives import utc_now_iso as _utc_now_iso


@dataclass(frozen=True)
class DecisionAdherenceEvent:
    strategy_id: str
    expected_entry_rule: str
    expected_exit_rule: str
    expected_sizing_rule: str
    observed_entry_rule: str
    observed_exit_rule: str
    observed_sizing_rule: str
    override_used: bool = False
    override_approved: bool = False
    override_severity: float = 0.0

    def __post_init__(self) -> None:
        if not str(self.strategy_id).strip():
            raise ValueError("strategy_id is required")
        severity = float(self.override_severity)
        if severity < 0.0 or severity > 1.0:
            raise ValueError("override_severity must be in [0, 1]")


@dataclass(frozen=True)
class StrategyAdherenceScore:
    strategy_id: str
    adherence_score: float
    approved_override_rate: float
    unapproved_drift_rate: float
    mean_override_severity: float
    total_events: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "adherence_score": float(self.adherence_score),
            "approved_override_rate": float(self.approved_override_rate),
            "unapproved_drift_rate": float(self.unapproved_drift_rate),
            "mean_override_severity": float(self.mean_override_severity),
            "total_events": int(self.total_events),
        }


@dataclass(frozen=True)
class OverrideBudgetDecision:
    allow_promotion: bool
    action: str
    reason_codes: tuple[str, ...]
    stage: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "allow_promotion": bool(self.allow_promotion),
            "action": self.action,
            "reason_codes": list(self.reason_codes),
            "stage": self.stage,
        }


@dataclass(frozen=True)
class RiskRewardPolicyReceipt:
    strategy_id: str
    order_id: str
    declared_stop: float
    declared_target: float
    declared_invalidate: str
    exit_price: float
    exit_reason: str
    policy_match: bool
    reason_code: str
    emitted_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "order_id": self.order_id,
            "declared_stop": float(self.declared_stop),
            "declared_target": float(self.declared_target),
            "declared_invalidate": self.declared_invalidate,
            "exit_price": float(self.exit_price),
            "exit_reason": self.exit_reason,
            "policy_match": bool(self.policy_match),
            "reason_code": self.reason_code,
            "emitted_at": self.emitted_at,
        }


@dataclass(frozen=True)
class CapitalEfficiencyMetrics:
    strategy_id: str
    net_pnl: float
    locked_capital: float
    order_count: int
    turnover: float
    pnl_per_locked_capital: float
    pnl_per_order: float
    pnl_per_turnover: float
    throughput_without_edge: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "net_pnl": float(self.net_pnl),
            "locked_capital": float(self.locked_capital),
            "order_count": int(self.order_count),
            "turnover": float(self.turnover),
            "pnl_per_locked_capital": float(self.pnl_per_locked_capital),
            "pnl_per_order": float(self.pnl_per_order),
            "pnl_per_turnover": float(self.pnl_per_turnover),
            "throughput_without_edge": bool(self.throughput_without_edge),
        }


@dataclass(frozen=True)
class SelfOffsetDetection:
    strategy_id: str
    market_id: str
    window_start: str
    window_end: str
    side_sequence: tuple[str, ...]
    net_exposure: float
    expected_spread_capture: float
    realized_spread_capture: float
    unexplained: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "market_id": self.market_id,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "side_sequence": list(self.side_sequence),
            "net_exposure": float(self.net_exposure),
            "expected_spread_capture": float(self.expected_spread_capture),
            "realized_spread_capture": float(self.realized_spread_capture),
            "unexplained": bool(self.unexplained),
        }


@dataclass(frozen=True)
class TradeCountVanityDecision:
    eligible_for_top_performer: bool
    reason_code: str
    details: dict[str, float]

    def as_dict(self) -> dict[str, Any]:
        return {
            "eligible_for_top_performer": bool(self.eligible_for_top_performer),
            "reason_code": self.reason_code,
            "details": dict(self.details),
        }


def _rule_match(expected: str, observed: str) -> bool:
    return str(expected).strip().lower() == str(observed).strip().lower()


def compute_strategy_adherence_score(
    events: list[DecisionAdherenceEvent],
) -> StrategyAdherenceScore:
    """Compute declared-rule adherence score and drift decomposition."""

    if not events:
        raise ValueError("at least one adherence event is required")
    strategy_ids = {row.strategy_id for row in events}
    if len(strategy_ids) != 1:
        raise ValueError("adherence events must belong to one strategy")

    approved_override = 0
    unapproved_drift = 0
    severities: list[float] = []
    aligned = 0
    for row in events:
        entry_ok = _rule_match(row.expected_entry_rule, row.observed_entry_rule)
        exit_ok = _rule_match(row.expected_exit_rule, row.observed_exit_rule)
        size_ok = _rule_match(row.expected_sizing_rule, row.observed_sizing_rule)
        row_aligned = entry_ok and exit_ok and size_ok

        if row.override_used and row.override_approved:
            approved_override += 1
            severities.append(float(row.override_severity))
            row_aligned = True
        elif row.override_used and not row.override_approved:
            unapproved_drift += 1
            severities.append(float(row.override_severity))
        elif not row_aligned:
            unapproved_drift += 1
        if row_aligned:
            aligned += 1

    total = len(events)
    return StrategyAdherenceScore(
        strategy_id=events[0].strategy_id,
        adherence_score=float(aligned) / float(total),
        approved_override_rate=float(approved_override) / float(total),
        unapproved_drift_rate=float(unapproved_drift) / float(total),
        mean_override_severity=float(mean(severities) if severities else 0.0),
        total_events=total,
    )


def evaluate_override_budget_and_drift_gate(
    *,
    score: StrategyAdherenceScore,
    stage: str,
    max_override_rate: float,
    max_unapproved_drift_rate: float,
    max_mean_severity: float,
) -> OverrideBudgetDecision:
    """Apply stage-aware action when override/drift budget is exceeded."""

    token_stage = str(stage).strip().lower() or "paper"
    reasons: list[str] = []
    if score.approved_override_rate > float(max_override_rate):
        reasons.append("override_budget_exceeded")
    if score.unapproved_drift_rate > float(max_unapproved_drift_rate):
        reasons.append("unapproved_drift_exceeded")
    if score.mean_override_severity > float(max_mean_severity):
        reasons.append("drift_severity_exceeded")
    if not reasons:
        return OverrideBudgetDecision(
            allow_promotion=True,
            action="pass",
            reason_codes=(),
            stage=token_stage,
        )

    stage_action = {
        "backtest": "hold",
        "paper": "hold",
        "shadow": "demote",
        "canary": "demote",
        "live": "kill-review",
    }.get(token_stage, "hold")
    return OverrideBudgetDecision(
        allow_promotion=False,
        action=stage_action,
        reason_codes=tuple(sorted(set(reasons))),
        stage=token_stage,
    )


def build_fixed_rr_policy_receipt(
    *,
    strategy_id: str,
    order_id: str,
    declared_stop: float,
    declared_target: float,
    declared_invalidate: str,
    exit_price: float,
    exit_reason: str,
) -> RiskRewardPolicyReceipt:
    """Persist fixed risk/reward policy receipt and mismatch reason code."""

    if float(declared_stop) <= 0.0 or float(declared_target) <= 0.0:
        raise ValueError("declared_stop and declared_target must be positive")
    if float(declared_stop) >= float(declared_target):
        raise ValueError("declared_stop must be below declared_target for long-style policy")

    reason = str(exit_reason).strip().lower()
    if reason in {"stop", "target", "invalidate", "approved_exception"}:
        match = True
        code = "policy_matched"
    else:
        match = False
        code = "rr_policy_mismatch"

    return RiskRewardPolicyReceipt(
        strategy_id=str(strategy_id).strip(),
        order_id=str(order_id).strip(),
        declared_stop=float(declared_stop),
        declared_target=float(declared_target),
        declared_invalidate=str(declared_invalidate).strip(),
        exit_price=float(exit_price),
        exit_reason=reason,
        policy_match=match,
        reason_code=code,
        emitted_at=_utc_now_iso(),
    )


def compute_capital_efficiency_metrics(
    *,
    strategy_id: str,
    net_pnl: float,
    locked_capital: float,
    order_count: int,
    turnover: float,
    throughput_flag_floor: float = 0.0005,
) -> CapitalEfficiencyMetrics:
    """Compute capital efficiency metrics and throughput-without-edge flag."""

    if float(locked_capital) <= 0.0:
        raise ValueError("locked_capital must be > 0")
    if int(order_count) <= 0:
        raise ValueError("order_count must be > 0")
    if float(turnover) <= 0.0:
        raise ValueError("turnover must be > 0")

    pnl_cap = float(net_pnl) / float(locked_capital)
    pnl_order = float(net_pnl) / float(order_count)
    pnl_turnover = float(net_pnl) / float(turnover)
    throughput_without_edge = bool(
        int(order_count) >= 25 and pnl_cap < float(throughput_flag_floor)
    )
    return CapitalEfficiencyMetrics(
        strategy_id=str(strategy_id).strip(),
        net_pnl=float(net_pnl),
        locked_capital=float(locked_capital),
        order_count=int(order_count),
        turnover=float(turnover),
        pnl_per_locked_capital=pnl_cap,
        pnl_per_order=pnl_order,
        pnl_per_turnover=pnl_turnover,
        throughput_without_edge=throughput_without_edge,
    )


def detect_same_market_self_offset(
    *,
    strategy_id: str,
    market_id: str,
    side_sequence: list[str],
    net_exposure: float,
    declared_two_sided_mode: bool,
    expected_spread_capture: float,
    realized_spread_capture: float,
    window_start: str,
    window_end: str,
) -> SelfOffsetDetection | None:
    """Detect unexplained opposite-side inventory churn in one market."""

    clean = [str(side).strip().upper() for side in side_sequence if str(side).strip()]
    has_both_sides = ("BUY" in clean) and ("SELL" in clean)
    if not has_both_sides:
        return None
    unexplained = bool(
        (not declared_two_sided_mode)
        and (abs(float(net_exposure)) < 0.10)
        and (float(realized_spread_capture) < float(expected_spread_capture) * 0.50)
    )
    return SelfOffsetDetection(
        strategy_id=str(strategy_id).strip(),
        market_id=str(market_id).strip(),
        window_start=str(window_start).strip(),
        window_end=str(window_end).strip(),
        side_sequence=tuple(clean),
        net_exposure=float(net_exposure),
        expected_spread_capture=float(expected_spread_capture),
        realized_spread_capture=float(realized_spread_capture),
        unexplained=unexplained,
    )


def evaluate_trade_count_vanity(
    *,
    candidate: CapitalEfficiencyMetrics,
    baseline: CapitalEfficiencyMetrics,
) -> TradeCountVanityDecision:
    """Prevent top-performer labeling when order count outruns real edge."""

    order_ratio = float(candidate.order_count) / float(max(baseline.order_count, 1))
    cap_eff_ratio = float(candidate.pnl_per_locked_capital) / float(
        max(abs(baseline.pnl_per_locked_capital), 1e-9)
    )
    turnover_eff_ratio = float(candidate.pnl_per_turnover) / float(
        max(abs(baseline.pnl_per_turnover), 1e-9)
    )
    if order_ratio >= 2.0 and (cap_eff_ratio < 1.0 or turnover_eff_ratio < 1.0):
        return TradeCountVanityDecision(
            eligible_for_top_performer=False,
            reason_code="trade_count_vanity",
            details={
                "order_ratio": order_ratio,
                "capital_efficiency_ratio": cap_eff_ratio,
                "turnover_efficiency_ratio": turnover_eff_ratio,
            },
        )
    return TradeCountVanityDecision(
        eligible_for_top_performer=True,
        reason_code="eligible",
        details={
            "order_ratio": order_ratio,
            "capital_efficiency_ratio": cap_eff_ratio,
            "turnover_efficiency_ratio": turnover_eff_ratio,
        },
    )
