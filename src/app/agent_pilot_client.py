"""Thin Python client for the agent pilot API surface."""

from __future__ import annotations

from dataclasses import dataclass as _raw_dataclass, field
from sys import version_info
from typing import Any, Protocol

import requests


class _RequestTransport(Protocol):
    """Protocol used by the client to support session swapping in tests."""

    def request(self, method: str, url: str, **kwargs: Any) -> Any: ...


def dataclass(*args, **kwargs):
    """Compatibility wrapper for environments without dataclass slots."""
    if version_info < (3, 10):
        kwargs.pop("slots", None)
    return _raw_dataclass(*args, **kwargs)


@dataclass(slots=True)
class AgentPilotAPIClient:
    """Client wrapper for `/v1/agent/*` control-plane endpoints."""

    base_url: str = "http://localhost:8000"
    token: str = ""
    timeout_seconds: float = 20.0
    transport: _RequestTransport | None = None
    _requests_session: requests.Session | None = field(default=None, init=False, repr=False)

    def _url(self, path: str) -> str:
        prefix = self.base_url.rstrip("/")
        suffix = path if path.startswith("/") else f"/{path}"
        return f"{prefix}{suffix}"

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        token = self.token.strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _request(self, method: str, path: str, *, params: dict[str, Any] | None = None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.transport is None:
            if self._requests_session is None:
                self._requests_session = requests.Session()
            client: _RequestTransport = self._requests_session
        else:
            client = self.transport
        response = client.request(
            method=method,
            url=self._url(path),
            headers=self._headers(),
            params=params,
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("agent pilot API returned non-object JSON payload")
        return data

    def get_context(self, *, agent_id: str | None = None) -> dict[str, Any]:
        params = {"agent_id": agent_id} if agent_id else None
        return self._request("GET", "/v1/agent/context", params=params)

    def get_policy(self, *, agent_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/agent/policies/{agent_id}")

    def upsert_policy(
        self,
        *,
        agent_id: str,
        capabilities: dict[str, bool] | None = None,
        max_pending_intents: int | None = None,
        risk_budget_pct: float | None = None,
        allowed_markets: list[str] | None = None,
        allowed_actions: list[str] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if capabilities is not None:
            payload["capabilities"] = capabilities
        if max_pending_intents is not None:
            payload["max_pending_intents"] = max_pending_intents
        if risk_budget_pct is not None:
            payload["risk_budget_pct"] = risk_budget_pct
        if allowed_markets is not None:
            payload["allowed_markets"] = allowed_markets
        if allowed_actions is not None:
            payload["allowed_actions"] = allowed_actions
        return self._request("PUT", f"/v1/agent/policies/{agent_id}", payload=payload)

    def create_intent(
        self,
        *,
        action: str,
        strategy_id: str,
        rationale: str,
        supporting_card_ids: list[str],
        current_metrics: dict[str, Any],
        gate_checks: dict[str, Any],
        risk_impact: dict[str, Any],
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "action": action,
            "strategy_id": strategy_id,
            "rationale": rationale,
            "supporting_card_ids": supporting_card_ids,
            "current_metrics": current_metrics,
            "gate_checks": gate_checks,
            "risk_impact": risk_impact,
        }
        if agent_id:
            payload["agent_id"] = agent_id
        return self._request("POST", "/v1/agent/intents", payload=payload)

    def get_intent(self, *, intent_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/agent/intents/{intent_id}")

    def simulate_intent(self, *, intent_id: str) -> dict[str, Any]:
        return self._request("POST", f"/v1/agent/intents/{intent_id}/simulate")

    def execute_intent(self, *, intent_id: str) -> dict[str, Any]:
        return self._request("POST", f"/v1/agent/intents/{intent_id}/execute")

    def get_receipt(self, *, receipt_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/agent/receipts/{receipt_id}")

    def list_hooks(self, *, agent_id: str | None = None) -> dict[str, Any]:
        params = {"agent_id": agent_id} if agent_id else None
        return self._request("GET", "/v1/agent/hooks", params=params)

    def create_hook(
        self,
        *,
        event_type: str,
        target_url: str,
        secret: str = "",
        retry_max: int = 3,
        backoff_seconds: int = 5,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "event_type": event_type,
            "target_url": target_url,
            "secret": secret,
            "retry_max": retry_max,
            "backoff_seconds": backoff_seconds,
        }
        if agent_id:
            payload["agent_id"] = agent_id
        return self._request("POST", "/v1/agent/hooks", payload=payload)

    def delete_hook(self, *, hook_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/v1/agent/hooks/{hook_id}")
