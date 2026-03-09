"""External I/O adapter layer for canonical PQTS architecture."""

from adapters.market_data import load_adapter_module
from adapters.registry import AdapterDescriptor, adapters_by_kind, default_adapter_descriptors

__all__ = [
    "AdapterDescriptor",
    "adapters_by_kind",
    "default_adapter_descriptors",
    "load_adapter_module",
]
