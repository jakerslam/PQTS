"""Tests for normalized multi-asset instrument contracts."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from contracts.instruments import normalize_instrument  # noqa: E402


def test_normalize_crypto_instrument_parses_base_quote_and_contract_type() -> None:
    row = normalize_instrument(venue="binance", symbol="BTC-USDT-PERP", market="crypto")
    payload = row.to_dict()
    assert payload["asset_class"] == "crypto"
    assert payload["base_asset"] == "BTC"
    assert payload["quote_asset"] == "USDT-PERP"
    assert payload["contract_type"] == "perpetual"


def test_normalize_equities_and_forex_paths() -> None:
    equity = normalize_instrument(venue="alpaca", symbol="aapl", market="equities").to_dict()
    forex = normalize_instrument(venue="oanda", symbol="EUR/USD", market="forex").to_dict()
    assert equity["asset_class"] == "equities"
    assert equity["base_asset"] == "AAPL"
    assert forex["asset_class"] == "forex"
    assert forex["base_asset"] == "EUR"
    assert forex["quote_asset"] == "USD"
