"""External I/O adapter layer for canonical PQTS architecture."""

from adapters.market_data import load_adapter_module
from adapters.provider_contracts import (
    ProviderErrorEnvelope,
    ProviderResponseEnvelope,
    call_with_envelope,
)
from adapters.registry import AdapterDescriptor, adapters_by_kind, default_adapter_descriptors
from adapters.retrieval_surface import (
    MultiSourceRetrievalSurface,
    RetrievalRecord,
    merge_retrieval_sources,
)

__all__ = [
    "AdapterDescriptor",
    "MultiSourceRetrievalSurface",
    "ProviderErrorEnvelope",
    "ProviderResponseEnvelope",
    "RetrievalRecord",
    "adapters_by_kind",
    "call_with_envelope",
    "default_adapter_descriptors",
    "load_adapter_module",
    "merge_retrieval_sources",
]
