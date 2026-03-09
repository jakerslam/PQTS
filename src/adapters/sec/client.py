"""SEC EDGAR HTTP client with compliant request identity enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from adapters.provider_contracts import ProviderResponseEnvelope, call_with_envelope


def validate_sec_user_agent(value: str) -> str:
    """Validate SEC-compliant requester identity User-Agent string."""
    agent = str(value or "").strip()
    if not agent:
        raise ValueError("SEC requester identity is required (`User-Agent`).")
    if "@" not in agent:
        raise ValueError(
            "SEC requester identity must include a contact (for example email) in User-Agent."
        )
    if len(agent) < 12:
        raise ValueError("SEC requester identity User-Agent is too short.")
    return agent


@dataclass(frozen=True)
class SECIdentityConfig:
    user_agent: str

    @classmethod
    def from_env(cls) -> "SECIdentityConfig":
        from os import getenv

        return cls(user_agent=validate_sec_user_agent(getenv("PQTS_SEC_USER_AGENT", "")))


class SECClient:
    """Minimal SEC API client for `data.sec.gov` endpoints."""

    def __init__(
        self,
        *,
        identity: SECIdentityConfig,
        base_url: str = "https://data.sec.gov",
        timeout_seconds: float = 20.0,
    ) -> None:
        self.identity = identity
        self.base_url = str(base_url).rstrip("/")
        self.timeout_seconds = float(timeout_seconds)
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": validate_sec_user_agent(identity.user_agent),
                "Accept-Encoding": "gzip, deflate",
                "Accept": "application/json",
            }
        )

    @property
    def headers(self) -> dict[str, str]:
        return dict(self._session.headers)

    def get_json(self, path: str) -> dict[str, Any]:
        cleaned = "/" + path.lstrip("/")
        url = f"{self.base_url}{cleaned}"
        response = self._session.get(url, timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("SEC response payload must be a JSON object.")
        return payload

    def get_json_enveloped(
        self,
        path: str,
        *,
        trace_id: str | None = None,
    ) -> ProviderResponseEnvelope[dict[str, Any]]:
        cleaned = "/" + path.lstrip("/")
        endpoint = f"{self.base_url}{cleaned}"
        return call_with_envelope(
            provider="sec",
            endpoint=endpoint,
            callback=lambda: self.get_json(cleaned),
            trace_id=trace_id,
        )
