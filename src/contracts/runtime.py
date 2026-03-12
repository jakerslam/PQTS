"""Runtime context contracts shared across application layers."""

from __future__ import annotations

from dataclasses import dataclass as _raw_dataclass, field
from sys import version_info
from typing import Any, Mapping


def dataclass(*args, **kwargs):
    """Compatibility wrapper for environments without dataclass slots."""
    if version_info < (3, 10):
        kwargs.pop("slots", None)
    return _raw_dataclass(*args, **kwargs)


@dataclass(slots=True)
class RuntimeContext:
    """Composition root context passed to module lifecycle hooks."""

    config_path: str
    config: Mapping[str, Any]
    engine: Any
    metadata: dict[str, Any] = field(default_factory=dict)
