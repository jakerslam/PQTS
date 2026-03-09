"""Base module implementation for registry-managed lifecycle hooks."""

from __future__ import annotations

from dataclasses import dataclass

from contracts import ModuleDescriptor, ModuleHealth, RuntimeContext, RuntimeModule


@dataclass
class StaticModule(RuntimeModule):
    """No-op module with explicit descriptor for deterministic architecture wiring."""

    descriptor: ModuleDescriptor
    _running: bool = False

    async def start(self, context: RuntimeContext) -> None:  # pragma: no cover - trivial
        self._running = True

    async def stop(self, context: RuntimeContext) -> None:  # pragma: no cover - trivial
        self._running = False

    def health(self) -> ModuleHealth:
        return ModuleHealth(status="up" if self._running else "idle")
