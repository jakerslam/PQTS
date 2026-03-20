from __future__ import annotations

from research.long_history_signal import (
    CoverageRow,
    build_coverage_manifest,
    combine_domain_models,
    evaluate_prior_only_safety,
    evaluate_recency_drift_controls,
    evaluate_throughput_budget,
    evaluate_walk_forward_split,
)


def test_coverage_manifest_tracks_per_asset_windows() -> None:
    manifest = build_coverage_manifest(
        rows=[
            CoverageRow(asset_class="forex", symbol="EURUSD", start_year=1970, end_year=2025, missing_ratio=0.01),
            CoverageRow(asset_class="crypto", symbol="BTCUSD", start_year=2011, end_year=2025, missing_ratio=0.05),
        ],
        schema_version="ml50.v1",
        survivorship_policy="explicit",
    )
    assert manifest.coverage_by_asset["forex"]["min_year"] == 1970
    assert manifest.coverage_by_asset["crypto"]["min_year"] == 2011


def test_walk_forward_split_flags_overlap_and_leakage() -> None:
    result = evaluate_walk_forward_split(
        train_years=[2018, 2019, 2020],
        test_years=[2020, 2021],
        feature_asof_safe=False,
        leakage_detected=True,
    )
    assert result.leakage_safe is False
    assert "overlapping_train_test_windows" in result.reason_codes


def test_ensemble_and_prior_only_safety_contracts() -> None:
    ensemble = combine_domain_models(
        component_probabilities={"forex": 0.55, "equities": 0.51, "crypto": 0.60},
        component_weights={"forex": 1.0, "equities": 1.0, "crypto": 0.5},
        component_confidence={"forex": 0.8, "equities": 0.7, "crypto": 0.6},
    )
    assert 0.0 <= ensemble.combined_probability <= 1.0

    prior = evaluate_prior_only_safety(
        prior_signal_supports_trade=True,
        primary_strategy_supports_trade=False,
        conflict_action="size_down",
    )
    assert prior.action == "size_down"


def test_recency_and_budget_controls_degrade_when_limits_breached() -> None:
    recency = evaluate_recency_drift_controls(
        drift_by_component={"forex": 0.1, "crypto": 0.4},
        max_component_drift=0.2,
        downweight_factor=0.5,
    )
    assert recency.action == "downweight"
    assert "crypto" in recency.downweighted_components

    budget = evaluate_throughput_budget(
        market_count=100,
        p95_latency_ms=800.0,
        max_latency_ms=250.0,
        skipped_candidates=50,
        max_skip_ratio=0.2,
    )
    assert budget.action == "degrade_to_shadow"
    assert "latency_budget_exceeded" in budget.reason_codes
