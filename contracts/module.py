"""Core runtime module contracts for the canonical PQTS architecture."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ModuleDescriptor:
    """Static metadata used by the runtime registry and architecture tooling."""

    name: str
    provides: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    description: str = ""


@dataclass
class ModuleHealth:
    """Runtime health snapshot for a module."""

    status: str = "unknown"
    details: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class RuntimeModule(Protocol):
    """Lifecycle contract every runtime module must satisfy."""

    descriptor: ModuleDescriptor

    async def start(self, context: "RuntimeContext") -> None:
        """Start module resources."""

    async def stop(self, context: "RuntimeContext") -> None:
        """Stop module resources."""

    def health(self) -> ModuleHealth:
        """Return current module health."""


# Imported at end to avoid circular imports at runtime.
from contracts.runtime import RuntimeContext  # noqa: E402  pylint: disable=wrong-import-position
