"""Edge-sign discipline controls for capital-affecting execution paths (SOPR)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass(frozen=True)
class EdgeSignInputs:
    model_probability: float | None
    market_probability: float | None
    expected_alpha_bps: float
    predicted_total_router_bps: float
    attempted_override: bool = False
    override_reason: str = ""


@dataclass(frozen=True)
class EdgeSignDecision:
    allow_execute: bool
    action: str
    raw_edge: float
    cost_adjusted_edge: float
    reason_code: str
    attempted_override: bool
    final_disposition: str
    override_reason: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "allow_execute": bool(self.allow_execute),
            "action": self.action,
            "raw_edge": float(self.raw_edge),
            "cost_adjusted_edge": float(self.cost_adjusted_edge),
            "reason_code": self.reason_code,
            "attempted_override": bool(self.attempted_override),
            "final_disposition": self.final_disposition,
            "override_reason": self.override_reason,
        }


@dataclass(frozen=True)
class SkipDisciplineDecision:
    allow_promotion: bool
    action: str
    reason_codes: Tuple[str, ...]
    candidate_to_trade_conversion: float
    non_positive_attempt_rate: float


@dataclass
class EdgeSignTelemetry:
    candidate_count: int = 0
    admitted_count: int = 0
    rejected_count: int = 0
    rejected_by_reason: Dict[str, int] = field(default_factory=dict)
    override_attempt_count: int = 0
    override_blocked_count: int = 0

    def record(self, decision: EdgeSignDecision) -> None:
        self.candidate_count += 1
        if decision.attempted_override:
            self.override_attempt_count += 1
        if decision.allow_execute:
            self.admitted_count += 1
            return
        self.rejected_count += 1
        self.rejected_by_reason[decision.reason_code] = (
            int(self.rejected_by_reason.get(decision.reason_code, 0)) + 1
        )
        if decision.attempted_override:
            self.override_blocked_count += 1

    def metrics(self) -> Dict[str, float | Dict[str, int]]:
        candidate = max(self.candidate_count, 1)
        return {
            "candidate_count": float(self.candidate_count),
            "admitted_count": float(self.admitted_count),
            "rejected_count": float(self.rejected_count),
            "candidate_to_trade_conversion": float(self.admitted_count) / float(candidate),
            "non_positive_attempt_rate": float(
                self.rejected_by_reason.get("non_positive_edge", 0)
            )
            / float(candidate),
            "override_attempt_count": float(self.override_attempt_count),
            "override_blocked_count": float(self.override_blocked_count),
            "rejected_by_reason": dict(self.rejected_by_reason),
        }


def _is_probability(token: float | None) -> bool:
    if token is None:
        return False
    value = float(token)
    return 0.0 <= value <= 1.0


def evaluate_edge_sign_gate(
    inputs: EdgeSignInputs,
    *,
    allow_override_simulation: bool,
) -> EdgeSignDecision:
    """Evaluate raw and cost-adjusted edge sign before execution eligibility."""

    if _is_probability(inputs.model_probability) and _is_probability(inputs.market_probability):
        raw_edge = float(inputs.model_probability or 0.0) - float(inputs.market_probability or 0.0)
    else:
        # Fallback keeps legacy strategies operable until probability payloads are onboarded.
        raw_edge = float(inputs.expected_alpha_bps) / 10000.0

    cost_adjusted_edge = raw_edge - (max(float(inputs.predicted_total_router_bps), 0.0) / 10000.0)
    non_positive = raw_edge <= 0.0 or cost_adjusted_edge <= 0.0

    if non_positive:
        if inputs.attempted_override:
            if allow_override_simulation:
                return EdgeSignDecision(
                    allow_execute=False,
                    action="shadow_only",
                    raw_edge=float(raw_edge),
                    cost_adjusted_edge=float(cost_adjusted_edge),
                    reason_code="non_positive_edge",
                    attempted_override=True,
                    final_disposition="shadow_only",
                    override_reason=str(inputs.override_reason).strip(),
                )
            return EdgeSignDecision(
                allow_execute=False,
                action="hold",
                raw_edge=float(raw_edge),
                cost_adjusted_edge=float(cost_adjusted_edge),
                reason_code="non_positive_edge",
                attempted_override=True,
                final_disposition="hold",
                override_reason=str(inputs.override_reason).strip(),
            )
        return EdgeSignDecision(
            allow_execute=False,
            action="block",
            raw_edge=float(raw_edge),
            cost_adjusted_edge=float(cost_adjusted_edge),
            reason_code="non_positive_edge",
            attempted_override=False,
            final_disposition="block",
            override_reason="",
        )

    return EdgeSignDecision(
        allow_execute=True,
        action="allow",
        raw_edge=float(raw_edge),
        cost_adjusted_edge=float(cost_adjusted_edge),
        reason_code="positive_edge",
        attempted_override=bool(inputs.attempted_override),
        final_disposition="allow",
        override_reason=str(inputs.override_reason).strip(),
    )


def evaluate_skip_discipline_gate(
    telemetry: EdgeSignTelemetry,
    *,
    max_non_positive_attempt_rate: float,
    min_conversion_ratio: float,
) -> SkipDisciplineDecision:
    """Derive promotion/throttle actions from skip-discipline quality metrics."""

    metrics = telemetry.metrics()
    conversion = float(metrics["candidate_to_trade_conversion"])
    non_positive_attempt_rate = float(metrics["non_positive_attempt_rate"])
    reasons = []
    action = "allow"

    if non_positive_attempt_rate > float(max_non_positive_attempt_rate):
        reasons.append("non_positive_edge_attempt_rate_exceeded")
    if conversion < float(min_conversion_ratio):
        reasons.append("candidate_to_trade_conversion_too_low")

    if reasons:
        action = "require_review"
        if non_positive_attempt_rate > (float(max_non_positive_attempt_rate) * 1.5):
            action = "throttle_or_disable"

    return SkipDisciplineDecision(
        allow_promotion=not bool(reasons),
        action=action,
        reason_codes=tuple(sorted(set(reasons))),
        candidate_to_trade_conversion=float(conversion),
        non_positive_attempt_rate=float(non_positive_attempt_rate),
    )
