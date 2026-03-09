"""Tests for cache-backed session tokens and rate limiting."""

from __future__ import annotations

from fastapi.testclient import TestClient

from services.api.app import create_app
from services.api.config import APISettings


def _settings(*, write_rpm: int = 120) -> APISettings:
    return APISettings(
        service_name="PQTS API Test",
        service_version="9.9.9",
        environment="test",
        auth_tokens="admin-token:admin,operator-token:operator,viewer-token:viewer",
        write_rate_limit_per_minute=write_rpm,
    )


def test_can_issue_session_token_and_reuse_for_auth() -> None:
    client = TestClient(create_app(_settings()))
    create = client.post("/v1/auth/sessions", headers={"Authorization": "Bearer viewer-token"})
    assert create.status_code == 200
    session_token = create.json()["session_token"]
    assert session_token.startswith("sess_")

    me = client.get("/v1/auth/me", headers={"X-Session-Token": session_token})
    assert me.status_code == 200
    payload = me.json()["identity"]
    assert payload["role"] == "viewer"
    assert payload["auth_scheme"] == "session"


def test_write_rate_limit_blocks_excess_requests() -> None:
    client = TestClient(create_app(_settings(write_rpm=1)))
    headers = {"Authorization": "Bearer operator-token"}
    payload = {
        "account_id": "paper-main",
        "severity": "warning",
        "message": "latency drift",
        "code": "latency_guard",
    }

    first = client.post("/v1/risk/incidents", json=payload, headers=headers)
    assert first.status_code == 200

    second = client.post("/v1/risk/incidents", json=payload, headers=headers)
    assert second.status_code == 429
    assert "Rate limit exceeded" in second.json()["detail"]
