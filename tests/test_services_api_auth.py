"""Tests for API authentication and role guard behavior."""

from __future__ import annotations

from fastapi.testclient import TestClient

from services.api.app import create_app
from services.api.config import APISettings


def _settings() -> APISettings:
    return APISettings(
        service_name="PQTS API Test",
        service_version="9.9.9",
        environment="test",
        enable_openapi=True,
        auth_tokens="admin-token:admin,operator-token:operator,viewer-token:viewer",
    )


def test_auth_me_requires_authentication() -> None:
    app = create_app(_settings())
    client = TestClient(app)

    response = client.get("/v1/auth/me")
    assert response.status_code == 401
    assert "Authentication required" in response.json()["detail"]


def test_auth_me_accepts_bearer_token() -> None:
    app = create_app(_settings())
    client = TestClient(app)

    response = client.get(
        "/v1/auth/me",
        headers={"Authorization": "Bearer viewer-token"},
    )
    assert response.status_code == 200
    payload = response.json()["identity"]
    assert payload["role"] == "viewer"
    assert payload["auth_scheme"] == "bearer"


def test_auth_me_accepts_session_token() -> None:
    app = create_app(_settings())
    client = TestClient(app)

    response = client.get("/v1/auth/me", headers={"X-Session-Token": "operator-token"})
    assert response.status_code == 200
    payload = response.json()["identity"]
    assert payload["role"] == "operator"
    assert payload["auth_scheme"] == "session"


def test_admin_endpoint_rejects_non_admin_role() -> None:
    app = create_app(_settings())
    client = TestClient(app)

    response = client.post(
        "/v1/admin/kill-switch",
        headers={"Authorization": "Bearer operator-token"},
    )
    assert response.status_code == 403
    assert "Insufficient role" in response.json()["detail"]


def test_admin_endpoint_allows_admin_role() -> None:
    app = create_app(_settings())
    client = TestClient(app)

    response = client.post(
        "/v1/admin/kill-switch",
        headers={"Authorization": "Bearer admin-token"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "kill_switch"
    assert payload["status"] == "accepted"
