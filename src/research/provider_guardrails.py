"""Provider guardrails and bounded retry/backoff wrappers for generation calls."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class ProviderGuardrailConfig:
    max_retries: int = 3
    initial_backoff_seconds: float = 0.25
    max_backoff_seconds: float = 2.0
    retryable_error_tokens: tuple[str, ...] = (
        "timeout",
        "rate limit",
        "temporarily unavailable",
        "connection reset",
    )


@dataclass(frozen=True)
class ProviderAttemptRecord:
    attempt: int
    success: bool
    error_message: str
    backoff_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderCallOutcome:
    success: bool
    response: Any
    attempts: list[ProviderAttemptRecord] = field(default_factory=list)
    final_error: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["attempts"] = [item.to_dict() for item in self.attempts]
        return payload


def _is_retryable_error(message: str, *, retryable_tokens: tuple[str, ...]) -> bool:
    lowered = message.lower()
    return any(token in lowered for token in retryable_tokens)


def run_with_provider_guardrails(
    *,
    call: Callable[[], Any],
    config: ProviderGuardrailConfig | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> ProviderCallOutcome:
    cfg = config or ProviderGuardrailConfig()
    if cfg.max_retries < 0:
        raise ValueError("max_retries must be >= 0")

    attempts: list[ProviderAttemptRecord] = []
    backoff = max(float(cfg.initial_backoff_seconds), 0.0)
    max_backoff = max(float(cfg.max_backoff_seconds), backoff)
    max_attempts = int(cfg.max_retries) + 1

    for attempt_idx in range(1, max_attempts + 1):
        try:
            response = call()
            attempts.append(
                ProviderAttemptRecord(
                    attempt=attempt_idx,
                    success=True,
                    error_message="",
                    backoff_seconds=0.0,
                )
            )
            return ProviderCallOutcome(success=True, response=response, attempts=attempts)
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            retryable = _is_retryable_error(message, retryable_tokens=cfg.retryable_error_tokens)
            is_last_attempt = attempt_idx >= max_attempts
            next_backoff = 0.0
            if retryable and not is_last_attempt:
                next_backoff = min(backoff, max_backoff)
                sleep_fn(next_backoff)
                backoff = min(max(backoff * 2.0, cfg.initial_backoff_seconds), max_backoff)
            attempts.append(
                ProviderAttemptRecord(
                    attempt=attempt_idx,
                    success=False,
                    error_message=message,
                    backoff_seconds=next_backoff,
                )
            )
            if not retryable or is_last_attempt:
                return ProviderCallOutcome(
                    success=False,
                    response=None,
                    attempts=attempts,
                    final_error=message,
                )

    return ProviderCallOutcome(
        success=False,
        response=None,
        attempts=attempts,
        final_error="unknown_provider_failure",
    )
