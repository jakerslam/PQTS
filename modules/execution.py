"""Execution module descriptor."""

from __future__ import annotations

from contracts import ModuleDescriptor
from modules.base import StaticModule


class ExecutionModule(StaticModule):
    def __init__(self) -> None:
        super().__init__(
            descriptor=ModuleDescriptor(
                name="execution",
                requires=("risk",),
                provides=("orders", "fills", "positions"),
                description="Routes approved intents to venues and captures fill state.",
            )
        )
