"""Tests for secret non-exposure helpers."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.secrets_policy import detect_secret_exposure, sanitize_secrets_for_logging


def test_sanitize_secrets_for_logging_redacts_secret_keys() -> None:
    payload = {
        "exchange": {
            "api_key": "k_live",
            "api_secret": "s_live",
            "name": "binance",
        },
        "token": "abc123",
    }
    redacted = sanitize_secrets_for_logging(payload)
    assert redacted["exchange"]["api_key"] == "***REDACTED***"
    assert redacted["exchange"]["api_secret"] == "***REDACTED***"
    assert redacted["exchange"]["name"] == "binance"
    assert redacted["token"] == "***REDACTED***"


def test_detect_secret_exposure_finds_known_secret_values() -> None:
    payload = {"logs": ["connected with key sk_live_supersecret_123"]}  # noqa: S106
    issues = detect_secret_exposure(
        payload,
        known_secret_values={"API_KEY": "sk_live_supersecret_123"},
    )
    assert len(issues) == 1
    assert issues[0].secret_name == "API_KEY"


def test_detect_secret_exposure_ignores_short_tokens() -> None:
    payload = {"logs": ["contains token abc"]}
    issues = detect_secret_exposure(payload, known_secret_values={"SHORT": "abc"})
    assert issues == []
