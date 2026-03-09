"""Risk module descriptor."""

from __future__ import annotations

from contracts import ModuleDescriptor
from modules.base import StaticModule


class RiskModule(StaticModule):
    def __init__(self) -> None:
        super().__init__(
            descriptor=ModuleDescriptor(
                name="risk",
                requires=("signals",),
                provides=("risk_decisions",),
                description="Applies gating, capacity, and safety controls.",
            )
        )
