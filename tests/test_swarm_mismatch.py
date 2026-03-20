from __future__ import annotations

from research.swarm_mismatch import (
    build_news_shock_resimulation_artifact,
    classify_attention_tier,
    evaluate_mismatch_decay,
    evaluate_multi_seed_stability,
)


def test_multi_seed_stability_fails_on_high_dispersion() -> None:
    decision = evaluate_multi_seed_stability(
        probabilities_by_seed={"a": 0.3, "b": 0.7, "c": 0.2, "d": 0.8},
        max_dispersion=0.05,
        min_seed_count=3,
        max_ci_half_width=0.15,
    )
    assert decision.allow_trade is False
    assert "seed_dispersion_exceeded" in decision.reason_codes


def test_news_shock_artifact_downgrades_on_stale_recompute() -> None:
    artifact = build_news_shock_resimulation_artifact(
        shock_ts="2026-03-20T12:00:00+00:00",
        ingest_ts="2026-03-20T12:00:01+00:00",
        recompute_ts="2026-03-20T12:05:30+00:00",
        prior_probability=0.42,
        updated_probability=0.55,
        max_recompute_latency_ms=30_000,
    )
    assert artifact.action == "shadow_only"
    assert artifact.probability_shift > 0.0


def test_attention_tier_classification_flags_low_attention() -> None:
    tier = classify_attention_tier(
        participants_24h=20,
        volume_24h_usd=10_000.0,
        update_rate_per_minute=0.2,
    )
    assert tier.tier == "low_attention"
    assert "edge_concentrated_low_attention" in tier.reason_codes


def test_mismatch_decay_blocks_when_post_cost_edge_falls_below_threshold() -> None:
    decision = evaluate_mismatch_decay(
        initial_mismatch=0.004,
        elapsed_seconds=1800,
        half_life_seconds=300,
        projected_cost_bps=7.0,
        min_post_cost_edge_bps=2.0,
    )
    assert decision.allow_execute is False
    assert "delay_adjusted_edge_below_threshold" in decision.reason_codes
