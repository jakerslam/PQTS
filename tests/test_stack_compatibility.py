from __future__ import annotations

from integrations.stack_compatibility import (
    FieldVerification,
    StackComponent,
    evaluate_dataset_verification,
    evaluate_stack_compatibility,
    evaluate_underlying_contract_bridge,
)


def test_stack_compatibility_fails_on_missing_capability() -> None:
    decision = evaluate_stack_compatibility(
        components=[
            StackComponent(
                component_id="mcp",
                layer="data",
                version="1.0.0",
                schema_version="2.1",
                capabilities=("quotes",),
            )
        ],
        required_layers=("data", "research", "simulation"),
        required_capabilities={"data": ("quotes", "trades")},
    )
    assert decision.compatible is False
    assert "missing_layer:research" in decision.reason_codes


def test_dataset_verification_blocks_when_coverage_low() -> None:
    decision = evaluate_dataset_verification(
        fields=[
            FieldVerification(field_name="headline", verification_status="verified", confidence=0.9),
            FieldVerification(field_name="rumor_score", verification_status="unverified", confidence=0.2),
        ],
        min_verified_coverage=0.75,
        min_confidence=0.8,
    )
    assert decision.allow_for_execution is False
    assert "verification_coverage_below_threshold" in decision.reason_codes


def test_underlying_bridge_blocks_on_low_confidence_and_staleness() -> None:
    decision = evaluate_underlying_contract_bridge(
        mapped_market_id="pm-1",
        bridge_confidence=0.4,
        bridge_as_of_ts="2026-03-20T11:00:00+00:00",
        now_ts="2026-03-20T12:00:00+00:00",
        max_bridge_age_ms=120000,
        max_bridge_latency_ms=1500,
        bridge_latency_ms=2200,
        underlying_edge_bps=8.0,
        translation_uncertainty_bps=10.0,
        min_delay_adjusted_edge_bps=1.0,
    )
    assert decision.allow_trade is False
    assert "bridge_confidence_low" in decision.reason_codes
    assert "bridge_stale" in decision.reason_codes
