"""Tests for standardized provider response/error envelopes."""

from __future__ import annotations

import requests

from adapters.provider_contracts import call_with_envelope
from adapters.sec.client import SECClient, SECIdentityConfig


def test_call_with_envelope_success_shape() -> None:
    envelope = call_with_envelope(
        provider="demo",
        endpoint="/demo",
        callback=lambda: {"ok": True},
        trace_id="trace-123",
    )
    assert envelope.ok is True
    assert envelope.data == {"ok": True}
    assert envelope.error is None
    assert envelope.trace_id == "trace-123"


def test_call_with_envelope_classifies_validation_error() -> None:
    envelope = call_with_envelope(
        provider="demo",
        endpoint="/demo",
        callback=lambda: (_ for _ in ()).throw(ValueError("bad input")),
    )
    assert envelope.ok is False
    assert envelope.error is not None
    assert envelope.error.category == "validation"
    assert envelope.error.retriable is False


def test_call_with_envelope_classifies_timeout() -> None:
    envelope = call_with_envelope(
        provider="demo",
        endpoint="/demo",
        callback=lambda: (_ for _ in ()).throw(requests.Timeout("timed out")),
    )
    assert envelope.ok is False
    assert envelope.error is not None
    assert envelope.error.category == "timeout"
    assert envelope.error.retriable is True


def test_sec_client_get_json_enveloped() -> None:
    class _Response:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"status": "ok"}

    client = SECClient(identity=SECIdentityConfig(user_agent="PQTSBot/1.0 (ops@pqts.dev)"))
    client._session.get = lambda _url, timeout: _Response()  # type: ignore[method-assign]

    envelope = client.get_json_enveloped("/files/company_tickers.json", trace_id="trace-sec")
    assert envelope.ok is True
    assert envelope.data == {"status": "ok"}
    assert envelope.trace_id == "trace-sec"
