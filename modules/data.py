"""Data module descriptor."""

from __future__ import annotations

from contracts import ModuleDescriptor
from modules.base import StaticModule


class DataModule(StaticModule):
    def __init__(self) -> None:
        super().__init__(
            descriptor=ModuleDescriptor(
                name="data",
                provides=("market_data", "reference_data", "snapshots"),
                description="Owns ingestion and normalized data contracts.",
            )
        )
