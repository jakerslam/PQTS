"""Tests for API deployment profile and runtime control resolution."""

from __future__ import annotations

from services.api.config import APISettings


def test_profile_defaults_canary(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("PQTS_API_DEPLOYMENT_PROFILE", "canary")
    monkeypatch.delenv("PQTS_API_WORKERS", raising=False)
    monkeypatch.delenv("PQTS_API_LIMIT_CONCURRENCY", raising=False)

    settings = APISettings.from_env()
    assert settings.deployment_profile == "canary"
    assert settings.workers == 2
    assert settings.limit_concurrency == 384


def test_profile_env_overrides(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("PQTS_API_DEPLOYMENT_PROFILE", "production")
    monkeypatch.setenv("PQTS_API_WORKERS", "8")
    monkeypatch.setenv("PQTS_API_LIMIT_CONCURRENCY", "2048")
    monkeypatch.setenv("PQTS_API_GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS", "90")

    settings = APISettings.from_env()
    assert settings.workers == 8
    assert settings.limit_concurrency == 2048
    assert settings.graceful_shutdown_timeout_seconds == 90
