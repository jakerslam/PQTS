"""Signals module descriptor."""

from __future__ import annotations

from contracts import ModuleDescriptor
from modules.base import StaticModule


class SignalsModule(StaticModule):
    def __init__(self) -> None:
        super().__init__(
            descriptor=ModuleDescriptor(
                name="signals",
                requires=("data",),
                provides=("trade_intents",),
                description="Transforms normalized data into strategy and model signals.",
            )
        )
