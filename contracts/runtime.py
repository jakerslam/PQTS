"""Runtime context contracts shared across application layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(slots=True)
class RuntimeContext:
    """Composition root context passed to module lifecycle hooks."""

    config_path: str
    config: Mapping[str, Any]
    engine: Any
    metadata: dict[str, Any] = field(default_factory=dict)
