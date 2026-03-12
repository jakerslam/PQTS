"""Strategy readiness and promotion gate evaluators."""

from __future__ import annotations

from dataclasses import dataclass

_STAGE_STATUS_ORDER = {
    "experimental": 0,
    "beta": 1,
    "active": 2,
    "certified": 3,
    "deprecated": -1,
}

_DEFAULT_REQUIRED_STATUS_BY_STAGE = {
    "paper": "beta",
    "canary": "certified",
    "live": "certified",
}


@dataclass(frozen=True)
class GateResult:
    passed: bool
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {"passed": self.passed, "reasons": list(self.reasons)}


@dataclass(frozen=True)
class BacktestThresholds:
    min_net_expectancy: float = 0.0
    min_calibration_stability: float = 0.80
    max_drawdown: float = 0.20


@dataclass(frozen=True)
class PaperThresholds:
    min_realized_alpha: float = 0.0
    min_sample_size: int = 100
    max_slippage_mape: float = 0.25


def _status_at_least(actual: str, required: str) -> bool:
    actual_score = _STAGE_STATUS_ORDER.get(str(actual).strip().lower(), -99)
    required_score = _STAGE_STATUS_ORDER.get(str(required).strip().lower(), -99)
    return actual_score >= required_score


def evaluate_adapter_stage_lockout(
    *,
    target_stage: str,
    adapter_provider: str,
    adapter_status: str,
    paper_ok: bool,
    required_status_by_stage: dict[str, str] | None = None,
) -> GateResult:
    stage = str(target_stage).strip().lower()
    if stage not in {"paper", "canary", "live"}:
        return GateResult(True, ())

    provider = str(adapter_provider).strip().lower()
    status = str(adapter_status).strip().lower()
    requirements = dict(required_status_by_stage or _DEFAULT_REQUIRED_STATUS_BY_STAGE)
    required_status = str(requirements.get(stage, "")).strip().lower()

    reasons: list[str] = []
    if stage == "paper" and not bool(paper_ok):
        reasons.append("adapter_paper_not_ready")
    if not required_status:
        reasons.append("adapter_stage_requirement_missing")
    elif not _status_at_least(status, required_status):
        reasons.append(
            f"adapter_stage_lockout:{provider}:{stage}:status={status}:required={required_status}"
        )
    return GateResult(not reasons, tuple(reasons))


def evaluate_backtest_readiness(
    *,
    net_expectancy: float,
    calibration_stability: float,
    max_drawdown_observed: float,
    thresholds: BacktestThresholds | None = None,
) -> GateResult:
    cfg = thresholds or BacktestThresholds()
    reasons: list[str] = []
    if net_expectancy <= cfg.min_net_expectancy:
        reasons.append("expectancy_not_positive")
    if calibration_stability < cfg.min_calibration_stability:
        reasons.append("calibration_unstable")
    if max_drawdown_observed > cfg.max_drawdown:
        reasons.append("drawdown_exceeds_tolerance")
    return GateResult(not reasons, tuple(reasons))


def evaluate_paper_trade_readiness(
    *,
    realized_net_alpha: float,
    sample_size: int,
    critical_violations: int,
    slippage_mape: float,
    thresholds: PaperThresholds | None = None,
) -> GateResult:
    cfg = thresholds or PaperThresholds()
    reasons: list[str] = []
    if realized_net_alpha <= cfg.min_realized_alpha:
        reasons.append("realized_alpha_not_positive")
    if sample_size < cfg.min_sample_size:
        reasons.append("sample_size_too_small")
    if critical_violations > 0:
        reasons.append("critical_risk_or_compliance_violation")
    if slippage_mape > cfg.max_slippage_mape:
        reasons.append("slippage_outside_tolerance")
    return GateResult(not reasons, tuple(reasons))


def evaluate_promotion_gate(
    *,
    paper_campaign_passed: bool,
    unresolved_high_severity_incidents: int,
    stress_replay_passed: bool,
    portfolio_limits_intact: bool,
) -> GateResult:
    reasons: list[str] = []
    if not paper_campaign_passed:
        reasons.append("paper_campaign_not_passed")
    if unresolved_high_severity_incidents > 0:
        reasons.append("open_high_severity_incidents")
    if not stress_replay_passed:
        reasons.append("stress_replay_failed")
    if not portfolio_limits_intact:
        reasons.append("portfolio_limits_not_intact")
    return GateResult(not reasons, tuple(reasons))
