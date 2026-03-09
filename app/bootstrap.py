"""Application composition root for canonical modular monolith wiring."""

from __future__ import annotations

from app.module_registry import ModuleRegistry
from contracts import RuntimeContext
from core.engine import TradingEngine
from modules import get_default_modules


def build_engine(config_path: str) -> TradingEngine:
    """Construct the trading engine instance."""

    return TradingEngine(config_path)


def build_module_registry() -> ModuleRegistry:
    """Construct and register built-in modules."""

    registry = ModuleRegistry()
    registry.register_many(get_default_modules())
    registry.resolve_start_order()
    return registry


def bootstrap_runtime(config_path: str) -> tuple[RuntimeContext, ModuleRegistry]:
    """Build runtime context and deterministic module registry."""

    engine = build_engine(config_path)
    context = RuntimeContext(
        config_path=config_path,
        config=engine.config,
        engine=engine,
        metadata={"architecture": "modular_monolith_v1"},
    )
    registry = build_module_registry()
    return context, registry
