"""Tests for the Ollama-backed agent pilot challenger."""

from __future__ import annotations

import json
from typing import Any

from app.ollama_agent_pilot import (
    OllamaPilotChallenger,
    OllamaPilotConfig,
    build_pilot_prompt,
    filter_retrievable_cards,
    sample_agent_context,
)


def _card(
    card_id: str = "mm_toxicity_filter_001", *, quality_score: float = 0.82
) -> dict[str, Any]:
    return {
        "card_id": card_id,
        "claim": "Validated toxicity filters improve market-making quality in high-vol regimes.",
        "quality": {"quality_score": quality_score, "min_quality_for_retrieval": 0.65},
        "decision_rules": [{"action": "promote_to_paper", "condition": "oos_sharpe >= 1"}],
    }


def _decision_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "action": "promote_to_paper",
        "strategy_id": "mm_toxicity_filter",
        "rationale": "OOS and deflated Sharpe evidence clears paper-only promotion threshold.",
        "supporting_card_ids": ["mm_toxicity_filter_001"],
        "current_metrics": {"oos_sharpe": 1.38, "deflated_sharpe": 1.11},
        "gate_checks": {"stage_gate": "backtest_to_paper", "kill_switch_clear": True},
        "risk_impact": {"risk_budget_pct": 0.5, "max_drawdown_pct": 0.09},
    }
    payload.update(overrides)
    return payload


def test_challenger_validates_strict_json_decision() -> None:
    captured: dict[str, Any] = {}

    def transport(payload: dict[str, Any], config: OllamaPilotConfig) -> dict[str, Any]:
        captured["payload"] = payload
        captured["config"] = config
        return {"message": {"content": json.dumps(_decision_payload())}}

    config = OllamaPilotConfig(model="test-model", base_url="http://localhost:11434")
    result = OllamaPilotChallenger(config=config, transport=transport).propose(
        sample_agent_context(),
        relevant_cards=[_card()],
    )

    assert result.is_valid is True
    assert result.decision is not None
    assert result.decision.action == "promote_to_paper"
    assert result.relevant_card_ids == ("mm_toxicity_filter_001",)
    assert captured["payload"]["format"] == "json"
    assert "SYSTEM_FACTS" in result.prompt
    assert "CURRENT_STATE" in result.prompt


def test_challenger_fails_closed_on_unsupported_action() -> None:
    def transport(payload: dict[str, Any], config: OllamaPilotConfig) -> dict[str, Any]:
        return {"message": {"content": json.dumps(_decision_payload(action="place_order"))}}

    result = OllamaPilotChallenger(transport=transport).propose(
        sample_agent_context(),
        relevant_cards=[_card()],
    )

    assert result.is_valid is False
    assert result.decision is None
    assert any("unsupported action" in error for error in result.validation_errors)


def test_quality_filter_keeps_only_retrievable_cards() -> None:
    cards = [_card("strong_card", quality_score=0.9), _card("weak_card", quality_score=0.3)]

    accepted = filter_retrievable_cards(cards, quality_threshold=0.65)
    prompt = build_pilot_prompt(sample_agent_context(), relevant_cards=accepted)

    assert [card["card_id"] for card in accepted] == ["strong_card"]
    assert "strong_card" in prompt
    assert "weak_card" not in prompt


def test_propose_and_create_intent_uses_existing_agent_api_contract() -> None:
    def transport(payload: dict[str, Any], config: OllamaPilotConfig) -> dict[str, Any]:
        return {"message": {"content": json.dumps(_decision_payload(action="hold"))}}

    class FakeClient:
        def __init__(self) -> None:
            self.created_payload: dict[str, Any] | None = None

        def create_intent(self, **kwargs: Any) -> dict[str, Any]:
            self.created_payload = kwargs
            return {"intent": {"intent_id": "intent_test"}}

        def simulate_intent(self, *, intent_id: str) -> dict[str, Any]:
            return {"intent": {"intent_id": intent_id, "status": "simulated"}}

    context = sample_agent_context(agent_id="agent-under-test")
    fake_client = FakeClient()
    result, created, simulation = OllamaPilotChallenger(
        transport=transport
    ).propose_and_create_intent(
        fake_client,  # type: ignore[arg-type]
        context,
        relevant_cards=[_card()],
        simulate=True,
    )

    assert result.is_valid is True
    assert fake_client.created_payload is not None
    assert fake_client.created_payload["agent_id"] == "agent-under-test"
    assert created == {"intent": {"intent_id": "intent_test"}}
    assert simulation == {"intent": {"intent_id": "intent_test", "status": "simulated"}}
