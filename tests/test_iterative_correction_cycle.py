from __future__ import annotations

from research.iterative_correction_cycle import (
    CorrectionCycleConfig,
    build_prediction_artifact,
    evaluate_cycle_diagnostics,
    evaluate_drift_recalibration,
    evaluate_early_stop,
    normalize_win_rate_claim,
)


def test_prediction_artifact_captures_cycle_metadata() -> None:
    artifact = build_prediction_artifact(
        config=CorrectionCycleConfig(
            objective="logloss",
            version="xgb-v3",
            configured_max_rounds=12,
            eta=0.05,
            stage="canary",
            horizon_seconds=3600,
        ),
        executed_rounds=20,
    )
    assert artifact.executed_rounds == 12
    assert artifact.configured_max_rounds == 12


def test_early_stop_fails_closed_to_hold() -> None:
    decision = evaluate_early_stop(
        converged=False,
        latency_ms=250,
        max_latency_ms=120,
        fallback_mode="hold",
    )
    assert decision.action == "hold"
    assert "latency_budget_exceeded" in decision.reason_codes


def test_cycle_diagnostics_rejects_non_beneficial_depth() -> None:
    diagnostics = evaluate_cycle_diagnostics(
        loss_deltas=[0.1, 0.2],
        residual_deltas=[0.05, 0.07],
        marginal_edge_contribution_bps=[0.1, 0.2],
        min_mean_edge_contribution_bps=1.0,
    )
    assert diagnostics.depth_beneficial is False
    assert "depth_not_beneficial" in diagnostics.reason_codes


def test_win_rate_claim_normalization_enforces_context_fields() -> None:
    normalized = normalize_win_rate_claim(
        wins=18,
        total=20,
        base_rate=0.5,
        confidence_interval_low=0.40,
        confidence_interval_high=0.95,
        horizon_segments=[],
        fee_slippage_assumptions_present=False,
    )
    assert normalized.normalized is False
    assert "sample_too_small" in normalized.reason_codes


def test_drift_recalibration_holds_without_valid_recalibration() -> None:
    decision = evaluate_drift_recalibration(
        residual_drift=0.6,
        calibration_drift=0.1,
        max_residual_drift=0.3,
        max_calibration_drift=0.2,
        has_valid_recalibration=False,
        rollback_safe=True,
    )
    assert decision.action == "hold"
    assert "missing_valid_recalibration" in decision.reason_codes
