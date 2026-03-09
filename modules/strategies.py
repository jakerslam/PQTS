"""Strategies module descriptor."""

from __future__ import annotations

from contracts import ModuleDescriptor
from modules.base import StaticModule


class StrategiesModule(StaticModule):
    def __init__(self) -> None:
        super().__init__(
            descriptor=ModuleDescriptor(
                name="strategies",
                requires=("signals", "risk"),
                provides=("strategy_set",),
                description="Hosts pluggable strategy modules and strategy metadata.",
            )
        )
