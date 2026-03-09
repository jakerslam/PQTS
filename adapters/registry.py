"""Adapter registry metadata for external I/O integrations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdapterDescriptor:
    name: str
    kind: str
    import_path: str


def default_adapter_descriptors() -> tuple[AdapterDescriptor, ...]:
    """Built-in market adapter bindings."""

    return (
        AdapterDescriptor("binance", "market_data", "markets.crypto.binance_adapter"),
        AdapterDescriptor("coinbase", "market_data", "markets.crypto.coinbase_adapter"),
        AdapterDescriptor("alpaca", "broker", "markets.equities.alpaca_adapter"),
        AdapterDescriptor("oanda", "broker", "markets.forex.oanda_adapter"),
    )


def adapters_by_kind(kind: str) -> list[AdapterDescriptor]:
    return [item for item in default_adapter_descriptors() if item.kind == kind]
