"""Tests for provider guardrail retry/backoff wrapper."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.provider_guardrails import ProviderGuardrailConfig, run_with_provider_guardrails


def test_run_with_provider_guardrails_retries_retryable_errors() -> None:
    attempts = {"count": 0}
    sleeps: list[float] = []

    def call() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("timeout from provider")
        return "ok"

    outcome = run_with_provider_guardrails(
        call=call,
        config=ProviderGuardrailConfig(max_retries=3, initial_backoff_seconds=0.1, max_backoff_seconds=0.5),
        sleep_fn=lambda seconds: sleeps.append(seconds),
    )
    assert outcome.success is True
    assert outcome.response == "ok"
    assert len(outcome.attempts) == 3
    assert sleeps == [0.1, 0.2]


def test_run_with_provider_guardrails_stops_on_non_retryable_error() -> None:
    def call() -> None:
        raise RuntimeError("invalid request payload")

    outcome = run_with_provider_guardrails(
        call=call,
        config=ProviderGuardrailConfig(max_retries=5),
        sleep_fn=lambda _seconds: None,
    )
    assert outcome.success is False
    assert len(outcome.attempts) == 1
    assert "invalid request" in outcome.final_error


def test_run_with_provider_guardrails_respects_max_retries() -> None:
    attempts = {"count": 0}

    def call() -> None:
        attempts["count"] += 1
        raise RuntimeError("rate limit from upstream")

    outcome = run_with_provider_guardrails(
        call=call,
        config=ProviderGuardrailConfig(max_retries=2, initial_backoff_seconds=0.05, max_backoff_seconds=0.05),
        sleep_fn=lambda _seconds: None,
    )
    assert outcome.success is False
    assert len(outcome.attempts) == 3  # first attempt + 2 retries
