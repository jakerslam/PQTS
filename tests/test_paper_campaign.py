"""Deterministic tests for paper campaign helpers."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from execution.paper_campaign import (
    build_portfolio_snapshot,
    build_probe_order,
    iter_cycle_symbols,
    select_symbol_price,
)
from execution.smart_router import OrderType


def test_build_portfolio_snapshot_exposures_and_leverage():
    snapshot = build_portfolio_snapshot(
        positions={"BTCUSDT": 0.5, "ETHUSDT": -2.0},
        prices={"BTCUSDT": 50000.0, "ETHUSDT": 3000.0},
        capital=100000.0,
    )

    assert snapshot["gross_exposure"] == 31000.0
    assert snapshot["net_exposure"] == 19000.0
    assert snapshot["leverage"] == 0.31


def test_select_symbol_price_skips_metadata_payloads():
    market_snapshot = {
        "last_price": 123.0,
        "vol_24h": 1_000_000,
        "binance": {
            "BTCUSDT": {"price": 51000.0, "spread": 0.0002, "volume_24h": 1000.0},
        },
    }

    selected = select_symbol_price(market_snapshot, "BTCUSDT")
    assert selected == ("binance", 51000.0)


def test_build_probe_order_uses_notional_and_order_type():
    order = build_probe_order(
        symbol="BTCUSDT",
        side="buy",
        notional_usd=200.0,
        price=50000.0,
        order_type=OrderType.LIMIT,
    )

    assert order.symbol == "BTCUSDT"
    assert order.side == "buy"
    assert order.order_type == OrderType.LIMIT
    assert order.quantity == pytest.approx(0.004)
    assert order.price == 50000.0


def test_iter_cycle_symbols_rejects_empty():
    with pytest.raises(ValueError):
        iter_cycle_symbols([])
