from __future__ import annotations

from execution.microstructure_quant_stack import (
    compute_avellaneda_stoikov_quote,
    evaluate_hawkes_intensity,
    evaluate_microstructure_simulation,
    evaluate_source_claim,
    evaluate_vpin_circuit,
)


def test_avellaneda_stoikov_quote_components() -> None:
    quote = compute_avellaneda_stoikov_quote(
        mid_price=100.0,
        inventory=5.0,
        risk_aversion=0.02,
        inventory_penalty=0.5,
        horizon_seconds=60,
        base_spread_bps=12.0,
        max_inventory_abs=10.0,
    )
    assert quote.bid <= quote.ask
    assert quote.spread > 0.0


def test_hawkes_fallback_when_invalid_parameters() -> None:
    decision = evaluate_hawkes_intensity(
        baseline_intensity=0.1,
        excitation=-0.2,
        decay=0.0,
        recent_event_count=20,
        max_intensity=5.0,
    )
    assert decision.stable is False
    assert decision.action == "fallback_conservative"


def test_vpin_circuit_transitions() -> None:
    paused = evaluate_vpin_circuit(
        vpin=0.95,
        high_threshold=0.9,
        medium_threshold=0.7,
        cooldown_elapsed_seconds=30,
        min_cooldown_seconds=120,
        health_revalidated=False,
    )
    assert paused.action == "pause"
    assert paused.cooldown_required is True

    resumed = evaluate_vpin_circuit(
        vpin=0.95,
        high_threshold=0.9,
        medium_threshold=0.7,
        cooldown_elapsed_seconds=180,
        min_cooldown_seconds=120,
        health_revalidated=True,
    )
    assert resumed.action == "resume"


def test_microstructure_evidence_and_claim_verification() -> None:
    sim = evaluate_microstructure_simulation(
        spread_capture_series=[0.5, 0.6, 0.4],
        drawdown_tail_p95=3.0,
        toxicity_trigger_rate=0.30,
        min_spread_capture_mean=0.2,
        max_drawdown_tail_p95=5.0,
        max_toxicity_trigger_rate=0.2,
    )
    assert sim.promotion_allowed is False
    assert "toxicity_trigger_rate_exceeded" in sim.reason_codes

    claim = evaluate_source_claim(has_trade_level_replay=False, has_controlled_rerun=False)
    assert claim.verification_status == "unverified"
    assert claim.allow_public_claim is False
