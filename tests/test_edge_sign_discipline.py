from __future__ import annotations

from execution.edge_sign_discipline import (
    EdgeSignInputs,
    EdgeSignTelemetry,
    evaluate_edge_sign_gate,
    evaluate_skip_discipline_gate,
)


def test_edge_sign_blocks_non_positive_edge() -> None:
    decision = evaluate_edge_sign_gate(
        EdgeSignInputs(
            model_probability=0.48,
            market_probability=0.50,
            expected_alpha_bps=-2.0,
            predicted_total_router_bps=1.0,
        ),
        allow_override_simulation=False,
    )
    assert decision.allow_execute is False
    assert decision.reason_code == "non_positive_edge"
    assert decision.final_disposition == "block"


def test_edge_sign_override_downgrades_to_shadow_only() -> None:
    decision = evaluate_edge_sign_gate(
        EdgeSignInputs(
            model_probability=0.49,
            market_probability=0.50,
            expected_alpha_bps=0.0,
            predicted_total_router_bps=0.5,
            attempted_override=True,
            override_reason="manual conviction",
        ),
        allow_override_simulation=True,
    )
    assert decision.allow_execute is False
    assert decision.final_disposition == "shadow_only"


def test_skip_discipline_gate_recommends_throttle() -> None:
    telemetry = EdgeSignTelemetry()
    for _ in range(5):
        telemetry.record(
            evaluate_edge_sign_gate(
                EdgeSignInputs(
                    model_probability=0.48,
                    market_probability=0.50,
                    expected_alpha_bps=-1.0,
                    predicted_total_router_bps=1.0,
                    attempted_override=True,
                ),
                allow_override_simulation=False,
            )
        )

    decision = evaluate_skip_discipline_gate(
        telemetry,
        max_non_positive_attempt_rate=0.2,
        min_conversion_ratio=0.1,
    )
    assert decision.allow_promotion is False
    assert decision.action == "throttle_or_disable"
    assert "non_positive_edge_attempt_rate_exceeded" in decision.reason_codes
