"""Tests for SEC request identity validation and client configuration."""

from __future__ import annotations

import pytest

from adapters.sec.client import SECClient, SECIdentityConfig, validate_sec_user_agent


def test_validate_sec_user_agent_rejects_missing_value() -> None:
    with pytest.raises(ValueError):
        validate_sec_user_agent("")


def test_validate_sec_user_agent_requires_contact_marker() -> None:
    with pytest.raises(ValueError):
        validate_sec_user_agent("pqts-bot")


def test_validate_sec_user_agent_accepts_compliant_value() -> None:
    value = validate_sec_user_agent("PQTSBot/1.0 (ops@pqts.dev)")
    assert value == "PQTSBot/1.0 (ops@pqts.dev)"


def test_sec_client_sets_user_agent_header() -> None:
    client = SECClient(identity=SECIdentityConfig(user_agent="PQTSBot/1.0 (ops@pqts.dev)"))
    assert "User-Agent" in client.headers
    assert client.headers["User-Agent"] == "PQTSBot/1.0 (ops@pqts.dev)"
