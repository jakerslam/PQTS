"""Standardized provider response/error envelopes for external adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Generic, TypeVar

import requests

T = TypeVar("T")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ProviderErrorEnvelope:
    provider: str
    category: str
    message: str
    retriable: bool
    status_code: int | None = None
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderResponseEnvelope(Generic[T]):
    provider: str
    endpoint: str
    ok: bool
    data: T | None
    error: ProviderErrorEnvelope | None
    requested_at: str
    received_at: str
    latency_ms: float
    trace_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.error is not None:
            payload["error"] = self.error.to_dict()
        return payload


def _classify_exception(provider: str, exc: Exception) -> ProviderErrorEnvelope:
    if isinstance(exc, requests.Timeout):
        return ProviderErrorEnvelope(
            provider=provider,
            category="timeout",
            message=str(exc),
            retriable=True,
        )
    if isinstance(exc, requests.HTTPError):
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)
        retriable = status_code is not None and int(status_code) >= 500
        return ProviderErrorEnvelope(
            provider=provider,
            category="http_error",
            message=str(exc),
            retriable=bool(retriable),
            status_code=int(status_code) if status_code is not None else None,
        )
    if isinstance(exc, requests.RequestException):
        return ProviderErrorEnvelope(
            provider=provider,
            category="network_error",
            message=str(exc),
            retriable=True,
        )
    if isinstance(exc, ValueError):
        return ProviderErrorEnvelope(
            provider=provider,
            category="validation",
            message=str(exc),
            retriable=False,
        )
    return ProviderErrorEnvelope(
        provider=provider,
        category="system",
        message=str(exc),
        retriable=False,
    )


def call_with_envelope(
    *,
    provider: str,
    endpoint: str,
    callback: Callable[[], T],
    trace_id: str | None = None,
) -> ProviderResponseEnvelope[T]:
    requested_at = _now_iso()
    start = datetime.now(timezone.utc)
    try:
        data = callback()
        end = datetime.now(timezone.utc)
        latency_ms = (end - start).total_seconds() * 1000.0
        return ProviderResponseEnvelope(
            provider=provider,
            endpoint=endpoint,
            ok=True,
            data=data,
            error=None,
            requested_at=requested_at,
            received_at=end.isoformat(),
            latency_ms=latency_ms,
            trace_id=trace_id,
        )
    except Exception as exc:
        end = datetime.now(timezone.utc)
        latency_ms = (end - start).total_seconds() * 1000.0
        return ProviderResponseEnvelope(
            provider=provider,
            endpoint=endpoint,
            ok=False,
            data=None,
            error=_classify_exception(provider, exc),
            requested_at=requested_at,
            received_at=end.isoformat(),
            latency_ms=latency_ms,
            trace_id=trace_id,
        )
