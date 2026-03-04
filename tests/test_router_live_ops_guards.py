"""Deterministic tests for router idempotency and live rate-limit guards."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from execution.risk_aware_router import RiskAwareRouter, VenueClient
from execution.smart_router import OrderRequest, OrderType
from risk.kill_switches import RiskLimits


def _market_data(symbol: str = "BTCUSDT") -> Dict[str, Any]:
    return {
        "binance": {
            symbol: {
                "price": 50000.0,
                "spread": 0.0002,
                "volume_24h": 2_000_000.0,
            }
        },
        "order_book": {
            "bids": [(49990.0, 2.0), (49980.0, 3.0)],
            "asks": [(50010.0, 2.0), (50020.0, 3.0)],
        },
    }


def _portfolio() -> Dict[str, Any]:
    return {
        "positions": {},
        "prices": {"BTCUSDT": 50000.0},
        "total_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "realized_pnl": 0.0,
        "gross_exposure": 0.0,
        "net_exposure": 0.0,
        "leverage": 0.0,
        "open_orders": [],
    }


def _router(tmp_path: Path, **broker_overrides: Any) -> RiskAwareRouter:
    broker_config = {
        "enabled": True,
        "live_execution": False,
        "tca_db_path": str(tmp_path / "tca.csv"),
        "order_ledger_path": str(tmp_path / "order_ledger.jsonl"),
    }
    broker_config.update(broker_overrides)
    router = RiskAwareRouter(
        risk_config=RiskLimits(
            max_daily_loss_pct=0.02,
            max_drawdown_pct=0.15,
            max_gross_leverage=2.0,
        ),
        broker_config=broker_config,
    )
    router.set_capital(100000.0, source="unit_test")
    return router


async def _submit(router: RiskAwareRouter, order: OrderRequest):
    return await router.submit_order(
        order=order,
        market_data=_market_data(order.symbol),
        portfolio=_portfolio(),
        strategy_returns={"baseline": [0.0] * 30},
        portfolio_changes=[0.0] * 30,
    )


def test_router_blocks_duplicate_client_order_intent(tmp_path):
    router = _router(tmp_path)
    order_1 = OrderRequest(
        symbol="BTCUSDT",
        side="buy",
        quantity=0.01,
        order_type=OrderType.LIMIT,
        price=50000.0,
        client_order_id="dup-1",
    )
    order_2 = OrderRequest(
        symbol="BTCUSDT",
        side="buy",
        quantity=0.01,
        order_type=OrderType.LIMIT,
        price=50000.0,
        client_order_id="dup-1",
    )

    first = asyncio.run(_submit(router, order_1))
    second = asyncio.run(_submit(router, order_2))

    assert first.success is True
    assert second.success is False
    assert "IDEMPOTENCY_DUPLICATE" in str(second.rejected_reason)
    stats = router.get_stats()
    assert stats["live_ops_controls"]["idempotency_rejects"] == 1


def test_live_router_requires_client_order_id_when_enabled(tmp_path):
    router = _router(tmp_path, live_execution=True, require_live_client_order_id=True)
    order = OrderRequest(
        symbol="BTCUSDT",
        side="buy",
        quantity=0.01,
        order_type=OrderType.LIMIT,
        price=50000.0,
    )

    result = asyncio.run(_submit(router, order))

    assert result.success is False
    assert result.rejected_reason == "LIVE_REQUIRES_CLIENT_ORDER_ID"


class _DummyLiveAdapter:
    def __init__(self):
        self.cancel_calls = 0

    async def place_order(self, **_kwargs: Any) -> Dict[str, Any]:
        return {"status": "accepted"}

    async def cancel_order(self, **_kwargs: Any) -> Dict[str, Any]:
        self.cancel_calls += 1
        return {"status": "cancelled"}


class _DummyMarketDataAdapter:
    def __init__(self):
        self.ticker_calls = 0
        self.orderbook_calls = 0

    async def get_ticker(self, _symbol: str) -> Dict[str, Any]:
        self.ticker_calls += 1
        return {
            "bidPrice": "59990",
            "askPrice": "60010",
            "lastPrice": "60000",
            "quoteVolume": "1000000",
        }

    async def get_orderbook(self, _symbol: str, limit: int = 5) -> Dict[str, Any]:
        _ = limit
        self.orderbook_calls += 1
        return {
            "bids": [("59990", "1.0"), ("59980", "2.0")],
            "asks": [("60010", "1.0"), ("60020", "2.0")],
        }


def test_live_router_blocks_rate_limited_venue_orders(tmp_path):
    router = _router(
        tmp_path,
        live_execution=True,
        require_live_client_order_id=True,
        rate_limits={
            "binance": {
                "order_create": {"limit": 1, "window_seconds": 60.0},
            }
        },
    )
    router.market_venues["binance"] = VenueClient(
        market="crypto",
        venue="binance",
        symbols=["BTCUSDT"],
        adapter=_DummyLiveAdapter(),
        connected=True,
        is_stub=False,
    )

    first = OrderRequest(
        symbol="BTCUSDT",
        side="buy",
        quantity=0.01,
        order_type=OrderType.LIMIT,
        price=50000.0,
        client_order_id="rl-1",
    )
    second = OrderRequest(
        symbol="BTCUSDT",
        side="buy",
        quantity=0.01,
        order_type=OrderType.LIMIT,
        price=50000.0,
        client_order_id="rl-2",
    )

    result_1 = asyncio.run(_submit(router, first))
    result_2 = asyncio.run(_submit(router, second))

    assert result_1.success is True
    assert result_2.success is False
    assert "RATE_LIMIT_EXCEEDED" in str(result_2.rejected_reason)
    stats = router.get_stats()
    assert stats["live_ops_controls"]["rate_limit_rejects"] == 1


def test_market_data_endpoint_rate_limits_gate_adapter_calls(tmp_path):
    router = _router(
        tmp_path,
        rate_limits={
            "binance": {
                "market_ticker": {"limit": 1, "window_seconds": 60.0},
                "market_order_book": {"limit": 1, "window_seconds": 60.0},
            }
        },
    )
    adapter = _DummyMarketDataAdapter()
    router.market_venues["binance"] = VenueClient(
        market="crypto",
        venue="binance",
        symbols=["BTCUSDT"],
        adapter=adapter,
        connected=True,
        is_stub=False,
    )

    first = asyncio.run(router.fetch_market_snapshot())
    second = asyncio.run(router.fetch_market_snapshot())

    assert first["binance"]["BTCUSDT"]["price"] == 60000.0
    assert adapter.ticker_calls == 1
    assert adapter.orderbook_calls == 1
    decisions = second.get("resilience", {}).get("decisions", [])
    binance_decision = next(
        (
            row
            for row in decisions
            if isinstance(row, dict)
            and row.get("venue") == "binance"
            and row.get("symbol") == "BTCUSDT"
        ),
        {},
    )
    assert binance_decision.get("mode") in {"replay", "synthetic", "failover"}

    stats = router.get_stats()
    denials = stats["live_ops_controls"]["rate_limit_denials_by_endpoint"]
    assert denials["binance:market_ticker"] >= 1


def test_cancel_live_order_uses_rate_limit_controls(tmp_path):
    router = _router(
        tmp_path,
        rate_limits={
            "binance": {
                "order_cancel": {"limit": 1, "window_seconds": 60.0},
            }
        },
    )
    adapter = _DummyLiveAdapter()
    router.market_venues["binance"] = VenueClient(
        market="crypto",
        venue="binance",
        symbols=["BTCUSDT"],
        adapter=adapter,
        connected=True,
        is_stub=False,
    )

    first = asyncio.run(
        router.cancel_live_order(
            exchange="binance",
            symbol="BTCUSDT",
            venue_order_id="123",
        )
    )
    second = asyncio.run(
        router.cancel_live_order(
            exchange="binance",
            symbol="BTCUSDT",
            venue_order_id="124",
        )
    )

    assert first is True
    assert second is False
    assert adapter.cancel_calls == 1
    stats = router.get_stats()
    assert stats["live_ops_controls"]["rate_limit_rejects"] == 1
    assert stats["live_ops_controls"]["rate_limit_denials_by_endpoint"]["binance:order_cancel"] >= 1


def test_router_blocks_strategy_from_disable_list(tmp_path):
    disable_path = tmp_path / "strategy_disable_list.json"
    disable_path.write_text(
        json.dumps(
            {
                "disabled_strategies": [
                    {"strategy_id": "disabled_alpha", "net_alpha_usd": -50.0, "trades": 100}
                ]
            }
        ),
        encoding="utf-8",
    )
    router = _router(
        tmp_path,
        strategy_disable_list_path=str(disable_path),
        strategy_disable_reload_seconds=0.0,
    )
    order = OrderRequest(
        symbol="BTCUSDT",
        side="buy",
        quantity=0.01,
        order_type=OrderType.LIMIT,
        price=50000.0,
        strategy_id="disabled_alpha",
        client_order_id="disable-1",
    )

    result = asyncio.run(_submit(router, order))
    assert result.success is False
    assert "STRATEGY_DISABLED_NEGATIVE_NET_ALPHA" in str(result.rejected_reason)
    stats = router.get_stats()
    assert stats["live_ops_controls"]["strategy_disable_rejects"] == 1


def test_router_enforces_strategy_allocation_cap(tmp_path):
    router = _router(
        tmp_path,
        allocation_controls={
            "enabled": True,
            "lookback_seconds": 3600,
            "default_max_strategy_allocation_pct": 0.10,
            "default_max_venue_allocation_pct": 1.0,
        },
    )
    first = OrderRequest(
        symbol="BTCUSDT",
        side="buy",
        quantity=0.18,
        order_type=OrderType.LIMIT,
        price=50000.0,
        strategy_id="strat_a",
        client_order_id="alloc-a-1",
    )
    second = OrderRequest(
        symbol="BTCUSDT",
        side="buy",
        quantity=0.05,
        order_type=OrderType.LIMIT,
        price=50000.0,
        strategy_id="strat_a",
        client_order_id="alloc-a-2",
    )

    result_1 = asyncio.run(_submit(router, first))
    result_2 = asyncio.run(_submit(router, second))

    assert result_1.success is True
    assert result_2.success is False
    assert "STRATEGY_ALLOCATION_CAP" in str(result_2.rejected_reason)


def test_router_enforces_venue_allocation_cap(tmp_path):
    router = _router(
        tmp_path,
        allocation_controls={
            "enabled": True,
            "lookback_seconds": 3600,
            "default_max_strategy_allocation_pct": 1.0,
            "default_max_venue_allocation_pct": 0.10,
        },
    )
    first = OrderRequest(
        symbol="BTCUSDT",
        side="buy",
        quantity=0.18,
        order_type=OrderType.LIMIT,
        price=50000.0,
        strategy_id="strat_a",
        client_order_id="alloc-v-1",
    )
    second = OrderRequest(
        symbol="BTCUSDT",
        side="buy",
        quantity=0.05,
        order_type=OrderType.LIMIT,
        price=50000.0,
        strategy_id="strat_b",
        client_order_id="alloc-v-2",
    )

    result_1 = asyncio.run(_submit(router, first))
    result_2 = asyncio.run(_submit(router, second))

    assert result_1.success is True
    assert result_2.success is False
    assert "VENUE_ALLOCATION_CAP" in str(result_2.rejected_reason)
