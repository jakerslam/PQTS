"""Tests for uncertainty-adjusted Kelly sizing."""

from __future__ import annotations

from portfolio.uncertainty_kelly import (
    UncertaintyKellyConfig,
    batch_uncertainty_kelly,
    uncertainty_adjusted_kelly,
)


def test_kelly_blocks_when_edge_below_minimum() -> None:
    decision = uncertainty_adjusted_kelly(
        market_id="m1",
        posterior_probability=0.52,
        payout_multiple=1.0,  # implied 0.5
        uncertainty=0.05,
        config=UncertaintyKellyConfig(min_edge=0.03),
    )
    assert decision.blocked is True
    assert decision.final_fraction == 0.0
    assert decision.reason == "edge_below_minimum"


def test_kelly_applies_uncertainty_penalty_and_caps_position() -> None:
    decision = uncertainty_adjusted_kelly(
        market_id="m2",
        posterior_probability=0.72,
        payout_multiple=1.5,
        uncertainty=0.20,
        config=UncertaintyKellyConfig(
            base_fraction=0.8,
            max_fraction=0.10,
            min_edge=0.01,
            uncertainty_penalty=1.0,
        ),
    )
    assert decision.blocked is False
    assert decision.full_kelly_fraction > 0.0
    assert decision.adjusted_fraction >= decision.final_fraction
    assert decision.final_fraction <= 0.10


def test_batch_uncertainty_kelly_returns_ordered_decisions() -> None:
    rows = batch_uncertainty_kelly(
        opportunities=[
            {"market_id": "a", "posterior_probability": 0.70, "payout_multiple": 1.2, "uncertainty": 0.05},
            {"market_id": "b", "posterior_probability": 0.49, "payout_multiple": 1.0, "uncertainty": 0.01},
        ],
        config=UncertaintyKellyConfig(min_edge=0.01),
    )
    assert [row.market_id for row in rows] == ["a", "b"]
    assert rows[0].final_fraction >= 0.0
