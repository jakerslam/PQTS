"""Helpers for loading market-data adapters through explicit descriptors."""

from __future__ import annotations

import importlib
from typing import Any

from adapters.registry import AdapterDescriptor


def load_adapter_module(descriptor: AdapterDescriptor) -> Any:
    """Dynamically load adapter module by explicit import path."""

    return importlib.import_module(descriptor.import_path)
