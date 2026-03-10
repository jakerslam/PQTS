"""Tests for the PQTS FastAPI API scaffold."""

from __future__ import annotations

from fastapi.testclient import TestClient

from services.api.app import create_app
from services.api.config import APISettings


def _build_settings(*, openapi: bool = True) -> APISettings:
    return APISettings(
        service_name="PQTS API Test",
        service_version="9.9.9",
        environment="test",
        host="127.0.0.1",
        port=8080,
        enable_openapi=openapi,
        database_url="postgresql://pqts:test@localhost:5432/pqts",
        redis_url="redis://localhost:6379/0",
    )


def test_health_endpoint_returns_service_payload() -> None:
    app = create_app(_build_settings())
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200

    payload = response.json()
    assert response.headers.get("x-trace-id", "").startswith("trace-")
    assert response.headers.get("x-run-id", "").startswith("run-")
    assert payload["status"] == "ok"
    assert payload["service"] == "PQTS API Test"
    assert payload["version"] == "9.9.9"
    assert payload["environment"] == "test"
    assert payload["runtime_controls"]["workers"] == 1
    assert "timestamp" in payload

    alias = client.get("/healthz")
    assert alias.status_code == 200
    assert alias.json()["status"] == "ok"


def test_ready_endpoint_includes_dependency_shape() -> None:
    app = create_app(_build_settings())
    client = TestClient(app)

    response = client.get("/ready")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["trace_id"].startswith("trace-")
    assert payload["run_id"].startswith("run-")
    assert payload["dependencies"]["database"]["configured"] is True
    assert payload["dependencies"]["redis"]["configured"] is True
    assert payload["dependencies"]["database"]["reachable"] in {True, False}
    assert payload["dependencies"]["redis"]["reachable"] in {True, False}
    assert payload["runtime_controls"]["limit_concurrency"] >= 1
    assert payload["shutdown_in_progress"] is False

    alias = client.get("/readyz")
    assert alias.status_code == 200
    assert alias.json()["status"] == "ready"


def test_openapi_enabled_by_default() -> None:
    app = create_app(_build_settings(openapi=True))
    client = TestClient(app)

    response = client.get("/openapi.json")
    assert response.status_code == 200
    payload = response.json()
    assert payload["info"]["title"] == "PQTS API Test"


def test_openapi_can_be_disabled() -> None:
    app = create_app(_build_settings(openapi=False))
    client = TestClient(app)

    response = client.get("/openapi.json")
    assert response.status_code == 404
