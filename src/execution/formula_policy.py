"""Formula-manifest compilation, context-sync, and copy-logic gate contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.compaction_primitives import utc_now_iso as _utc_now_iso


_STAGE_ORDER = ("backtest", "paper", "shadow", "canary", "live")


@dataclass(frozen=True)
class FormulaSpec:
    formula_id: str
    kind: str
    expression: str
    enabled: bool = True

    def __post_init__(self) -> None:
        if not str(self.formula_id).strip():
            raise ValueError("formula_id is required")
        if not str(self.kind).strip():
            raise ValueError("kind is required")
        if not str(self.expression).strip():
            raise ValueError("expression is required")


@dataclass(frozen=True)
class FormulaDrivenManifest:
    strategy_id: str
    version: str
    formulas: tuple[FormulaSpec, ...]
    risk_bounds: dict[str, float]
    stage_constraints: tuple[str, ...]

    def __post_init__(self) -> None:
        if not str(self.strategy_id).strip():
            raise ValueError("strategy_id is required")
        if not str(self.version).strip():
            raise ValueError("version is required")
        if not self.formulas:
            raise ValueError("at least one formula is required")
        required_risk = {"max_position_pct", "max_daily_loss_pct"}
        missing = sorted(required_risk.difference(self.risk_bounds.keys()))
        if missing:
            raise ValueError(f"missing required risk fields: {', '.join(missing)}")
        if not self.stage_constraints:
            raise ValueError("stage_constraints are required")


@dataclass(frozen=True)
class CompiledFormulaPolicy:
    strategy_id: str
    source_manifest_version: str
    compiled_version: str
    normalized_parameters: dict[str, float]
    validation_errors: tuple[str, ...]
    compiled_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "source_manifest_version": self.source_manifest_version,
            "compiled_version": self.compiled_version,
            "normalized_parameters": dict(self.normalized_parameters),
            "validation_errors": list(self.validation_errors),
            "compiled_at": self.compiled_at,
        }


@dataclass(frozen=True)
class FormulaDecisionReceipt:
    strategy_id: str
    decision_id: str
    manifest_version: str
    formula_inputs: dict[str, float]
    formula_outputs: dict[str, float]
    produced_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "decision_id": self.decision_id,
            "manifest_version": self.manifest_version,
            "formula_inputs": dict(self.formula_inputs),
            "formula_outputs": dict(self.formula_outputs),
            "produced_at": self.produced_at,
        }


@dataclass(frozen=True)
class DivergenceSentinelDecision:
    allow_trade: bool
    divergence_metric: float
    expected_net_edge_bps: float
    reason_codes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "allow_trade": bool(self.allow_trade),
            "divergence_metric": float(self.divergence_metric),
            "expected_net_edge_bps": float(self.expected_net_edge_bps),
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class FreshnessGateDecision:
    allow_trade: bool
    reason_codes: tuple[str, ...]
    signal_age_ms: int
    time_left_seconds: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "allow_trade": bool(self.allow_trade),
            "reason_codes": list(self.reason_codes),
            "signal_age_ms": int(self.signal_age_ms),
            "time_left_seconds": int(self.time_left_seconds),
        }


@dataclass(frozen=True)
class ContextSyncReceipt:
    origin_surface: str
    requested_action: str
    resolved_action: str
    config_version: str
    eligibility_state: str
    conflict_detected: bool
    emitted_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "origin_surface": self.origin_surface,
            "requested_action": self.requested_action,
            "resolved_action": self.resolved_action,
            "config_version": self.config_version,
            "eligibility_state": self.eligibility_state,
            "conflict_detected": bool(self.conflict_detected),
            "emitted_at": self.emitted_at,
        }


@dataclass(frozen=True)
class CopyLogicEligibilityDecision:
    eligible: bool
    resolved_action: str
    reason_codes: tuple[str, ...]
    stage: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "eligible": bool(self.eligible),
            "resolved_action": self.resolved_action,
            "reason_codes": list(self.reason_codes),
            "stage": self.stage,
        }


def compile_formula_manifest_to_policy(manifest: FormulaDrivenManifest) -> CompiledFormulaPolicy:
    """Compile formula manifest to deterministic versioned policy artifact."""

    errors: list[str] = []
    if not all(row.enabled for row in manifest.formulas):
        errors.append("disabled_formula_present")
    if "backtest" not in {str(item).strip().lower() for item in manifest.stage_constraints}:
        errors.append("missing_backtest_stage_constraint")
    if errors:
        raise RuntimeError(";".join(sorted(set(errors))))

    normalized = {str(k): float(v) for k, v in manifest.risk_bounds.items()}
    compiled_version = f"{manifest.version}.compiled"
    return CompiledFormulaPolicy(
        strategy_id=manifest.strategy_id,
        source_manifest_version=manifest.version,
        compiled_version=compiled_version,
        normalized_parameters=normalized,
        validation_errors=(),
        compiled_at=_utc_now_iso(),
    )


def build_formula_decision_receipt(
    *,
    strategy_id: str,
    decision_id: str,
    manifest_version: str,
    formula_inputs: dict[str, float],
    formula_outputs: dict[str, float],
) -> FormulaDecisionReceipt:
    """Persist concrete formula input/output values for tradable decisions."""

    if not formula_outputs:
        raise ValueError("formula_outputs are required")
    return FormulaDecisionReceipt(
        strategy_id=str(strategy_id).strip(),
        decision_id=str(decision_id).strip(),
        manifest_version=str(manifest_version).strip(),
        formula_inputs={str(k): float(v) for k, v in formula_inputs.items()},
        formula_outputs={str(k): float(v) for k, v in formula_outputs.items()},
        produced_at=_utc_now_iso(),
    )


def evaluate_correlated_market_divergence(
    *,
    divergence_metric: float,
    expected_net_edge_bps: float,
    min_divergence: float = 0.10,
    min_net_edge_bps: float = 5.0,
) -> DivergenceSentinelDecision:
    """Fail closed when divergence is not economically tradeable after costs."""

    reasons: list[str] = []
    if float(divergence_metric) < float(min_divergence):
        reasons.append("divergence_below_threshold")
    if float(expected_net_edge_bps) < float(min_net_edge_bps):
        reasons.append("net_edge_below_threshold")
    allow = not bool(reasons)
    return DivergenceSentinelDecision(
        allow_trade=allow,
        divergence_metric=float(divergence_metric),
        expected_net_edge_bps=float(expected_net_edge_bps),
        reason_codes=tuple(sorted(set(reasons))),
    )


def evaluate_short_horizon_freshness(
    *,
    signal_age_ms: int,
    time_left_seconds: int,
    max_signal_age_ms: int,
    min_time_left_seconds: int,
) -> FreshnessGateDecision:
    """Require minimum time-left and freshness before short-horizon execution."""

    reasons: list[str] = []
    if int(signal_age_ms) > int(max_signal_age_ms):
        reasons.append("signal_age_exceeded")
    if int(time_left_seconds) < int(min_time_left_seconds):
        reasons.append("insufficient_time_left")
    return FreshnessGateDecision(
        allow_trade=not bool(reasons),
        reason_codes=tuple(sorted(set(reasons))),
        signal_age_ms=int(signal_age_ms),
        time_left_seconds=int(time_left_seconds),
    )


def build_context_sync_receipt(
    *,
    origin_surface: str,
    requested_action: str,
    config_version: str,
    eligibility_state: str,
    conflict_detected: bool,
) -> ContextSyncReceipt:
    """Build bounded assistant-terminal sync receipt with safe default conflict handling."""

    req = str(requested_action).strip().lower() or "propose"
    eligible = str(eligibility_state).strip().lower() or "unknown"
    if conflict_detected or eligible not in {"eligible", "paper_only", "propose_only"}:
        resolved = "hold"
    elif req == "execute" and eligible != "eligible":
        resolved = "propose"
    else:
        resolved = req
    return ContextSyncReceipt(
        origin_surface=str(origin_surface).strip().lower(),
        requested_action=req,
        resolved_action=resolved,
        config_version=str(config_version).strip(),
        eligibility_state=eligible,
        conflict_detected=bool(conflict_detected),
        emitted_at=_utc_now_iso(),
    )


def evaluate_copy_logic_stage_bounded_eligibility(
    *,
    stage: str,
    prior_stage: str,
    leader_id: str,
    allowed_leaders: set[str],
    requested_notional: float,
    per_source_notional_cap: float,
    router_path_enforced: bool,
    gate_evaluators_passed: bool,
) -> CopyLogicEligibilityDecision:
    """Enforce stage progression and source/risk bounds for copy/follow logic."""

    token_stage = str(stage).strip().lower()
    token_prior = str(prior_stage).strip().lower()
    reasons: list[str] = []

    if token_stage not in _STAGE_ORDER or token_prior not in _STAGE_ORDER:
        reasons.append("invalid_stage")
    else:
        if _STAGE_ORDER.index(token_stage) > _STAGE_ORDER.index(token_prior) + 1:
            reasons.append("stage_skip_not_allowed")
    if str(leader_id).strip() not in allowed_leaders:
        reasons.append("leader_not_allowlisted")
    if float(requested_notional) > float(per_source_notional_cap):
        reasons.append("per_source_risk_cap_exceeded")
    if not bool(router_path_enforced):
        reasons.append("router_path_not_enforced")
    if not bool(gate_evaluators_passed):
        reasons.append("stage_gate_evaluator_failed")

    eligible = not bool(reasons)
    return CopyLogicEligibilityDecision(
        eligible=eligible,
        resolved_action="execute" if eligible else "hold",
        reason_codes=tuple(sorted(set(reasons))),
        stage=token_stage,
    )
