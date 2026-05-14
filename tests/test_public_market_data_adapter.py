from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from execution.risk_aware_router import RiskAwareRouter
from markets.crypto.binance_adapter import BinancePublicMarketDataAdapter
from markets.crypto.coinbase_adapter import CoinbasePublicMarketDataAdapter
from risk.kill_switches import RiskLimits


def _router() -> RiskAwareRouter:
    return RiskAwareRouter(
        risk_config=RiskLimits(),
        broker_config={"enabled": True, "live_execution": False},
    )


def test_router_builds_binance_public_market_data_adapter_without_credentials() -> None:
    router = _router()
    router.configure_market_adapters(
        {
            "crypto": {
                "enabled": True,
                "exchanges": [
                    {
                        "name": "binance",
                        "symbols": ["BTCUSDT"],
                        "public_market_data": True,
                        "public_market_data_live": True,
                    }
                ],
            }
        }
    )

    venue = router.market_venues["binance"]
    assert isinstance(venue.adapter, BinancePublicMarketDataAdapter)
    assert venue.is_stub is False
    assert venue.adapter.market_data_only is True
    assert venue.adapter.base_url == "https://api.binance.com"


def test_binance_public_market_data_stream_registry_has_market_only_channel() -> None:
    router = _router()
    router.configure_market_adapters(
        {
            "crypto": {
                "enabled": True,
                "exchanges": [
                    {
                        "name": "binance",
                        "symbols": ["BTCUSDT"],
                        "public_market_data": True,
                    }
                ],
            }
        }
    )

    registry = router.get_stream_registry()
    streams = registry["binance"]["streams"]
    assert registry["binance"]["available"] is True
    assert set(streams) == {"market"}
    assert streams["market"]["url"] == "wss://stream.binance.com:9443/ws"


def test_binance_public_market_data_adapter_rejects_orders() -> None:
    router = _router()
    adapter = BinancePublicMarketDataAdapter(router_token=router._create_token())

    with pytest.raises(RuntimeError, match="market-data only"):
        asyncio.run(adapter.place_order(symbol="BTCUSDT", side="buy", quantity=0.01))


def test_binance_missing_credentials_without_public_market_data_stays_stub() -> None:
    router = _router()
    router.configure_market_adapters(
        {
            "crypto": {
                "enabled": True,
                "exchanges": [{"name": "binance", "symbols": ["BTCUSDT"]}],
            }
        }
    )

    venue = router.market_venues["binance"]
    assert venue.adapter is None
    assert venue.is_stub is True


def test_router_builds_coinbase_public_market_data_adapter_without_credentials() -> None:
    router = _router()
    router.configure_market_adapters(
        {
            "crypto": {
                "enabled": True,
                "exchanges": [
                    {
                        "name": "coinbase",
                        "symbols": ["BTC-USD"],
                        "public_market_data": True,
                        "public_market_data_live": True,
                    }
                ],
            }
        }
    )

    venue = router.market_venues["coinbase"]
    assert isinstance(venue.adapter, CoinbasePublicMarketDataAdapter)
    assert venue.is_stub is False
    assert venue.adapter.market_data_only is True
    assert venue.adapter.base_url == "https://api.exchange.coinbase.com"


def test_coinbase_public_market_data_adapter_rejects_orders() -> None:
    router = _router()
    adapter = CoinbasePublicMarketDataAdapter(router_token=router._create_token())

    with pytest.raises(RuntimeError, match="market-data only"):
        asyncio.run(adapter.place_order(product_id="BTC-USD", side="buy", size=0.01))
