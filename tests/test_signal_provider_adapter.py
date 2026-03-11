from __future__ import annotations

import pytest

from integrations.signal_provider_adapter import (
    evaluate_provider_health,
    normalize_provider_signal,
)


def test_normalize_provider_signal_passes_for_valid_read_only_payload() -> None:
    payload = normalize_provider_signal(
        {
            "signal_id": "sig-1",
            "event_ts": "2026-03-11T12:00:00+00:00",
            "confidence": 0.82,
            "headline": "Shipping disruption detected",
        },
        provider="kreo",
        schema_version="1.0",
        entitlement_valid=True,
    )
    assert payload["provider"] == "kreo"
    assert payload["read_only"] is True
    assert payload["payload"]["headline"] == "Shipping disruption detected"


def test_normalize_provider_signal_blocks_write_keys() -> None:
    with pytest.raises(ValueError):
        normalize_provider_signal(
            {
                "signal_id": "sig-2",
                "event_ts": "2026-03-11T12:00:00+00:00",
                "confidence": 0.4,
                "submit_order": True,
            },
            provider="kreo",
            schema_version="1.0",
            entitlement_valid=True,
        )


def test_provider_health_marks_degraded_when_stale_or_entitlement_invalid() -> None:
    health = evaluate_provider_health(
        last_ingest_ts="2026-03-11T12:00:00+00:00",
        entitlement_valid=False,
        schema_drift_detected=False,
        now_ts="2026-03-11T12:02:30+00:00",
        max_age_seconds=30.0,
    )
    assert health.status == "degraded"
    assert "entitlement_invalid" in health.reason_codes
    assert "stale_provider_feed" in health.reason_codes
