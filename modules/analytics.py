"""Analytics module descriptor."""

from __future__ import annotations

from contracts import ModuleDescriptor
from modules.base import StaticModule


class AnalyticsModule(StaticModule):
    def __init__(self) -> None:
        super().__init__(
            descriptor=ModuleDescriptor(
                name="analytics",
                requires=("execution",),
                provides=("telemetry", "reports"),
                description="Computes diagnostics, attribution, and ops health views.",
            )
        )
