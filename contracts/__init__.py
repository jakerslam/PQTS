"""Canonical architecture contracts package."""

from contracts.events import EventEnvelope
from contracts.module import ModuleDescriptor, ModuleHealth, RuntimeModule
from contracts.runtime import RuntimeContext

__all__ = [
    "EventEnvelope",
    "ModuleDescriptor",
    "ModuleHealth",
    "RuntimeContext",
    "RuntimeModule",
]
