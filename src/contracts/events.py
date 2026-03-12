"""Shared event envelope contracts for cross-module communication."""

from __future__ import annotations

from dataclasses import dataclass as _raw_dataclass, field
from datetime import datetime, timezone
from sys import version_info
from typing import Any


def dataclass(*args, **kwargs):
    """Compatibility wrapper for environments without dataclass slots."""
    if version_info < (3, 10):
        kwargs.pop("slots", None)
    return _raw_dataclass(*args, **kwargs)


@dataclass(slots=True)
class EventEnvelope:
    """Minimal typed event envelope used for module boundary handoffs."""

    event_type: str
    source: str
    payload: dict[str, Any]
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
