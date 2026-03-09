"""Shared event envelope contracts for cross-module communication."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class EventEnvelope:
    """Minimal typed event envelope used for module boundary handoffs."""

    event_type: str
    source: str
    payload: dict[str, Any]
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
