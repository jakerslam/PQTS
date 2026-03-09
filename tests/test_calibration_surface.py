"""Tests for calibration surface and mispricing diagnostics pipeline."""

from __future__ import annotations

from analytics.calibration_surface import (
    CalibrationObservation,
    build_calibration_surface,
    diagnose_mispricing,
    run_calibration_mispricing_pipeline,
)


def test_build_calibration_surface_groups_by_regime_and_bucket() -> None:
    observations = [
        CalibrationObservation("m1", 0.72, 1.0, regime="high_vol"),
        CalibrationObservation("m2", 0.68, 0.0, regime="high_vol"),
        CalibrationObservation("m3", 0.32, 0.0, regime="range"),
        CalibrationObservation("m4", 0.35, 1.0, regime="range"),
    ]
    surface = build_calibration_surface(observations, bucket_edges=(0.0, 0.5, 1.0))
    assert len(surface) == 2
    by_regime = {row.regime: row for row in surface}
    assert by_regime["high_vol"].samples == 2
    assert by_regime["range"].samples == 2
    assert by_regime["high_vol"].bucket_label == "[0.50,1.00)"


def test_diagnose_mispricing_emits_ranked_signals() -> None:
    signals = diagnose_mispricing(
        posterior_probabilities={"a": 0.70, "b": 0.35, "c": 0.51},
        implied_probabilities={"a": 0.58, "b": 0.50, "c": 0.50},
        regime_by_market={"a": "high_vol", "b": "range", "c": "normal"},
        min_edge=0.05,
    )
    assert [row.market_id for row in signals] == ["b", "a"]
    assert signals[0].action == "sell"
    assert signals[1].action == "buy"


def test_pipeline_returns_surface_and_signals_summary() -> None:
    payload = run_calibration_mispricing_pipeline(
        observations=[
            CalibrationObservation("m1", 0.6, 1.0, regime="trend"),
            CalibrationObservation("m2", 0.4, 0.0, regime="trend"),
        ],
        posterior_probabilities={"m1": 0.6},
        implied_probabilities={"m1": 0.4},
        regime_by_market={"m1": "trend"},
        min_edge=0.05,
    )
    assert payload["summary"]["surface_rows"] >= 1
    assert payload["summary"]["signals"] == 1
    assert payload["mispricing_signals"][0]["market_id"] == "m1"
