"""Tests for API websocket stream channels."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from services.api.app import create_app
from services.api.config import APISettings


def _settings() -> APISettings:
    return APISettings(
        service_name="PQTS API Test",
        service_version="9.9.9",
        environment="test",
        auth_tokens="admin-token:admin,operator-token:operator,viewer-token:viewer",
    )


def _operator() -> dict[str, str]:
    return {"Authorization": "Bearer operator-token"}


def test_orders_channel_streams_snapshot_and_broadcast_update() -> None:
    client = TestClient(create_app(_settings()))
    now = datetime.now(timezone.utc).isoformat()
    order_payload = {
        "order_id": "ord-ws-1",
        "account_id": "paper-main",
        "symbol": "BTC-USD",
        "side": "buy",
        "order_type": "limit",
        "status": "open",
        "quantity": 2.0,
        "filled_quantity": 0.0,
        "remaining_quantity": 2.0,
        "submitted_at": now,
        "updated_at": now,
        "limit_price": 42_000.0,
        "time_in_force": "gtc",
    }

    with client.websocket_connect("/ws/orders?token=viewer-token&account_id=paper-main") as websocket:
        first = websocket.receive_json()
        assert first["channel"] == "orders"
        assert first["event"] == "snapshot"
        assert first["trace_id"].startswith("trace-")
        assert first["run_id"].startswith("run-")

        write = client.post("/v1/execution/orders", json=order_payload, headers=_operator())
        assert write.status_code == 200

        event = websocket.receive_json()
        assert event["channel"] == "orders"
        assert event["event"] == "order_appended"
        assert event["trace_id"].startswith("trace-")
        assert event["run_id"].startswith("run-")
        assert event["payload"]["order"]["order_id"] == "ord-ws-1"


def test_risk_channel_streams_incident_broadcast() -> None:
    client = TestClient(create_app(_settings()))
    payload = {
        "account_id": "paper-main",
        "severity": "critical",
        "message": "Kill switch activated",
        "code": "kill_switch",
    }

    with client.websocket_connect("/ws/risk?token=viewer-token&account_id=paper-main") as websocket:
        first = websocket.receive_json()
        assert first["event"] == "snapshot"
        assert first["trace_id"].startswith("trace-")
        assert first["run_id"].startswith("run-")

        write = client.post("/v1/risk/incidents", json=payload, headers=_operator())
        assert write.status_code == 200

        event = websocket.receive_json()
        assert event["channel"] == "risk"
        assert event["event"] == "risk_incident"
        assert event["trace_id"].startswith("trace-")
        assert event["run_id"].startswith("run-")
        assert event["payload"]["incident"]["code"] == "kill_switch"


def test_ws_rejects_invalid_token() -> None:
    client = TestClient(create_app(_settings()))
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/orders?token=invalid-token"):
            pass
    assert exc_info.value.code == 4401
