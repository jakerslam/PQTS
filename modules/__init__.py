"""Runtime module descriptors used by the canonical composition root."""

from __future__ import annotations

from modules.analytics import AnalyticsModule
from modules.data import DataModule
from modules.execution import ExecutionModule
from modules.risk import RiskModule
from modules.signals import SignalsModule
from modules.strategies import StrategiesModule


def get_default_modules() -> list:
    """Return built-in module instances in declaration order."""

    return [
        DataModule(),
        SignalsModule(),
        RiskModule(),
        StrategiesModule(),
        ExecutionModule(),
        AnalyticsModule(),
    ]


__all__ = [
    "AnalyticsModule",
    "DataModule",
    "ExecutionModule",
    "RiskModule",
    "SignalsModule",
    "StrategiesModule",
    "get_default_modules",
]
