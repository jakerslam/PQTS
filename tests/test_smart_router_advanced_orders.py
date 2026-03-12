"""Tests for advanced order-type coverage in smart router."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from execution.smart_router import OrderRequest, OrderType, SmartOrderRouter  # noqa: E402


def _market_data() -> dict:
    return {
        "binance": {
            "BTCUSDT": {
                "price": 100.0,
                "spread": 0.0005,
                "volume_24h": 1_000_000.0,
                "bid": 99.95,
                "ask": 100.05,
            }
        }
    }


def test_router_honors_explicit_advanced_order_types() -> None:
    router = SmartOrderRouter({"enabled": True, "exchanges": {"binance": {"fees": {"maker": 0.0, "taker": 0.0}}}})
    request = OrderRequest(
        symbol="BTCUSDT",
        side="buy",
        quantity=0.25,
        order_type=OrderType.POST_ONLY,
        price=99.95,
        time_in_force="GTC",
        strategy_id="maker_alpha",
    )
    decision = asyncio.run(router.route_order(request, _market_data()))
    assert decision.order_type == OrderType.POST_ONLY


def test_router_supports_pov_split_plans() -> None:
    router = SmartOrderRouter({"enabled": True, "max_single_order_size": 1.0, "pov_participation_rate": 0.1})
    request = OrderRequest(
        symbol="BTCUSDT",
        side="buy",
        quantity=3.0,
        order_type=OrderType.POV,
        price=100.0,
        strategy_id="pov_strategy",
    )
    decision = asyncio.run(router.route_order(request, _market_data()))
    assert decision.order_type == OrderType.POV
    assert len(decision.split_orders) >= 2
    assert all(order.order_type in {OrderType.POV, OrderType.LIMIT} for order in decision.split_orders)
