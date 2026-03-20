"""Iterative correction-cycle model governance contracts (MRPH family)."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import List, Tuple


@dataclass(frozen=True)
class CorrectionCycleConfig:
    objective: str
    version: str
    configured_max_rounds: int
    eta: float
    stage: str
    horizon_seconds: int


@dataclass(frozen=True)
class PredictionArtifact:
    objective: str
    version: str
    configured_max_rounds: int
    executed_rounds: int
    eta: float
    stage: str
    horizon_seconds: int


@dataclass(frozen=True)
class EarlyStopDecision:
    action: str
    converged: bool
    latency_ms: int
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class CycleDiagnostics:
    marginal_edge_contribution_bps: float
    average_loss_delta: float
    average_residual_delta: float
    depth_beneficial: bool
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class WinRateClaimNormalization:
    normalized: bool
    sample_size: int
    base_rate: float
    confidence_interval_low: float
    confidence_interval_high: float
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class DriftRecalibrationDecision:
    action: str
    rollback_safe: bool
    reason_codes: Tuple[str, ...]


def build_prediction_artifact(
    *,
    config: CorrectionCycleConfig,
    executed_rounds: int,
) -> PredictionArtifact:
    rounds = max(0, min(int(executed_rounds), int(config.configured_max_rounds)))
    return PredictionArtifact(
        objective=str(config.objective).strip(),
        version=str(config.version).strip(),
        configured_max_rounds=int(config.configured_max_rounds),
        executed_rounds=rounds,
        eta=float(config.eta),
        stage=str(config.stage).strip(),
        horizon_seconds=int(config.horizon_seconds),
    )


def evaluate_early_stop(
    *,
    converged: bool,
    latency_ms: int,
    max_latency_ms: int,
    fallback_mode: str,
) -> EarlyStopDecision:
    reasons: List[str] = []
    if not converged:
        reasons.append("convergence_not_reached")
    if int(latency_ms) > int(max_latency_ms):
        reasons.append("latency_budget_exceeded")

    if not reasons:
        return EarlyStopDecision(
            action="allow",
            converged=True,
            latency_ms=int(latency_ms),
            reason_codes=(),
        )

    action = str(fallback_mode).strip().lower() or "hold"
    if action not in {"hold", "shadow_only", "validated_snapshot"}:
        action = "hold"
    return EarlyStopDecision(
        action=action,
        converged=bool(converged),
        latency_ms=int(latency_ms),
        reason_codes=tuple(sorted(set(reasons))),
    )


def evaluate_cycle_diagnostics(
    *,
    loss_deltas: List[float],
    residual_deltas: List[float],
    marginal_edge_contribution_bps: List[float],
    min_mean_edge_contribution_bps: float,
) -> CycleDiagnostics:
    reasons: List[str] = []
    avg_loss_delta = float(mean(loss_deltas)) if loss_deltas else 0.0
    avg_residual_delta = float(mean(residual_deltas)) if residual_deltas else 0.0
    avg_edge = float(mean(marginal_edge_contribution_bps)) if marginal_edge_contribution_bps else 0.0

    if avg_edge < float(min_mean_edge_contribution_bps):
        reasons.append("depth_not_beneficial")
    if avg_loss_delta >= 0.0:
        reasons.append("loss_not_improving")
    if avg_residual_delta >= 0.0:
        reasons.append("residual_not_improving")

    return CycleDiagnostics(
        marginal_edge_contribution_bps=avg_edge,
        average_loss_delta=avg_loss_delta,
        average_residual_delta=avg_residual_delta,
        depth_beneficial=not bool(reasons),
        reason_codes=tuple(sorted(set(reasons))),
    )


def normalize_win_rate_claim(
    *,
    wins: int,
    total: int,
    base_rate: float,
    confidence_interval_low: float,
    confidence_interval_high: float,
    horizon_segments: List[str],
    fee_slippage_assumptions_present: bool,
) -> WinRateClaimNormalization:
    reasons: List[str] = []
    if int(total) <= 0:
        reasons.append("empty_sample")
    if int(total) < 30:
        reasons.append("sample_too_small")
    if not horizon_segments:
        reasons.append("missing_horizon_segmentation")
    if not fee_slippage_assumptions_present:
        reasons.append("missing_fee_slippage_assumptions")
    if float(confidence_interval_low) > float(confidence_interval_high):
        reasons.append("invalid_confidence_interval")

    return WinRateClaimNormalization(
        normalized=not bool(reasons),
        sample_size=int(total),
        base_rate=float(base_rate),
        confidence_interval_low=float(confidence_interval_low),
        confidence_interval_high=float(confidence_interval_high),
        reason_codes=tuple(sorted(set(reasons))),
    )


def evaluate_drift_recalibration(
    *,
    residual_drift: float,
    calibration_drift: float,
    max_residual_drift: float,
    max_calibration_drift: float,
    has_valid_recalibration: bool,
    rollback_safe: bool,
) -> DriftRecalibrationDecision:
    reasons: List[str] = []
    drift_triggered = False
    if float(residual_drift) > float(max_residual_drift):
        reasons.append("residual_drift_exceeded")
        drift_triggered = True
    if float(calibration_drift) > float(max_calibration_drift):
        reasons.append("calibration_drift_exceeded")
        drift_triggered = True

    if not drift_triggered:
        return DriftRecalibrationDecision(action="allow", rollback_safe=bool(rollback_safe), reason_codes=())

    if not has_valid_recalibration:
        reasons.append("missing_valid_recalibration")
        return DriftRecalibrationDecision(
            action="hold",
            rollback_safe=bool(rollback_safe),
            reason_codes=tuple(sorted(set(reasons))),
        )

    if not rollback_safe:
        reasons.append("rollback_not_safe")
        return DriftRecalibrationDecision(
            action="shadow_only",
            rollback_safe=False,
            reason_codes=tuple(sorted(set(reasons))),
        )

    return DriftRecalibrationDecision(
        action="recalibrate",
        rollback_safe=True,
        reason_codes=tuple(sorted(set(reasons))),
    )
