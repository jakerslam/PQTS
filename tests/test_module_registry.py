"""Tests for canonical module registry behavior."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.module_registry import ModuleRegistry
from contracts import ModuleDescriptor, ModuleHealth, RuntimeContext


@dataclass
class _TestModule:
    descriptor: ModuleDescriptor
    started: bool = False

    async def start(self, context: RuntimeContext) -> None:
        self.started = True

    async def stop(self, context: RuntimeContext) -> None:
        self.started = False

    def health(self) -> ModuleHealth:
        return ModuleHealth(status="up" if self.started else "idle")


def _context() -> RuntimeContext:
    return RuntimeContext(config_path="config/paper.yaml", config={}, engine=object())


def test_resolve_start_order_uses_dependencies():
    registry = ModuleRegistry()
    registry.register(
        _TestModule(ModuleDescriptor(name="data"))
    )
    registry.register(
        _TestModule(ModuleDescriptor(name="signals", requires=("data",)))
    )
    registry.register(
        _TestModule(ModuleDescriptor(name="risk", requires=("signals",)))
    )

    assert registry.resolve_start_order() == ["data", "signals", "risk"]


def test_resolve_start_order_rejects_unknown_dependency():
    registry = ModuleRegistry()
    registry.register(_TestModule(ModuleDescriptor(name="signals", requires=("data",))))

    with pytest.raises(ValueError, match="unknown module"):
        registry.resolve_start_order()


def test_resolve_start_order_rejects_cycles():
    registry = ModuleRegistry()
    registry.register(_TestModule(ModuleDescriptor(name="a", requires=("b",))))
    registry.register(_TestModule(ModuleDescriptor(name="b", requires=("a",))))

    with pytest.raises(ValueError, match="cyclic module dependency"):
        registry.resolve_start_order()


def test_start_and_stop_all_are_ordered():
    registry = ModuleRegistry()
    one = _TestModule(ModuleDescriptor(name="one"))
    two = _TestModule(ModuleDescriptor(name="two", requires=("one",)))
    registry.register(one)
    registry.register(two)

    started = asyncio.run(registry.start_all(_context()))
    assert started == ["one", "two"]
    assert one.started is True and two.started is True

    stopped = asyncio.run(registry.stop_all(_context()))
    assert stopped == ["two", "one"]
    assert one.started is False and two.started is False
