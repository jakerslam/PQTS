"""Tests for the Python agent pilot API client wrapper."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agent_pilot_client import AgentPilotAPIClient
from services.api.app import create_app
from services.api.config import APISettings


def _settings() -> APISettings:
    return APISettings(
        service_name="PQTS API Test",
        service_version="9.9.9",
        environment="test",
        auth_tokens="admin-token:admin,operator-token:operator,viewer-token:viewer",
    )


class _TestTransport:
    def __init__(self, client: TestClient) -> None:
        self._client = client

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        kwargs.pop("timeout", None)
        return self._client.request(method=method, url=url, **kwargs)


def _client(test_client: TestClient, token: str) -> AgentPilotAPIClient:
    return AgentPilotAPIClient(
        base_url="http://testserver",
        token=token,
        transport=_TestTransport(test_client),
    )


def test_agent_client_intent_flow_and_receipt_lookup() -> None:
    test_client = TestClient(create_app(_settings()))
    viewer = _client(test_client, "viewer-token")
    operator = _client(test_client, "operator-token")

    context = viewer.get_context()
    agent_id = context["agent_id"]
    default_policy = viewer.get_policy(agent_id=agent_id)["policy"]
    assert default_policy["capabilities"]["execute"] is False

    policy = operator.upsert_policy(
        agent_id=agent_id,
        capabilities={
            "read": True,
            "propose": True,
            "simulate": True,
            "execute": True,
            "hooks_manage": True,
        },
    )["policy"]
    assert policy["capabilities"]["execute"] is True

    created = viewer.create_intent(
        action="promote_to_paper",
        strategy_id="trend_following",
        rationale="sustained paper stability",
        supporting_card_ids=["card_a", "card_b"],
        current_metrics={"fill_rate": 0.91, "reject_rate": 0.02},
        gate_checks={"paper_days": 45},
        risk_impact={"delta_var_pct": 0.3},
    )
    intent_id = created["intent"]["intent_id"]
    assert created["intent"]["status"] == "proposed"

    simulated = viewer.simulate_intent(intent_id=intent_id)
    assert simulated["intent"]["status"] == "simulated"
    assert simulated["simulation"]["passed"] is True

    executed = operator.execute_intent(intent_id=intent_id)
    assert executed["intent"]["status"] == "executed"
    assert executed["receipt"]["type"] == "intent_executed"
    receipt_id = executed["receipt"]["receipt_id"]

    receipt = viewer.get_receipt(receipt_id=receipt_id)
    assert receipt["receipt"]["receipt_id"] == receipt_id


def test_agent_client_hook_lifecycle_and_allowlist_guard() -> None:
    test_client = TestClient(create_app(_settings()))
    viewer = _client(test_client, "viewer-token")

    with pytest.raises(httpx.HTTPStatusError):
        viewer.create_hook(
            event_type="intent_status",
            target_url="https://evil.example.com/webhook",
        )

    created = viewer.create_hook(
        event_type="risk_incident",
        target_url="https://hooks.slack.com/services/T000/B000/XYZ",
        secret="super-secret",
        retry_max=4,
        backoff_seconds=9,
    )
    hook = created["hook"]
    hook_id = hook["hook_id"]
    assert hook["target_host"] == "hooks.slack.com"
    assert hook["secret_fingerprint"] != ""

    rows = viewer.list_hooks()["hooks"]
    assert any(item["hook_id"] == hook_id for item in rows)

    deleted = viewer.delete_hook(hook_id=hook_id)
    assert deleted["hook"]["status"] == "deleted"
