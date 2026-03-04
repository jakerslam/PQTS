"""Deterministic tests for execution-model tuning enhancements."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.engine import TradingEngine
from execution.paper_fill_model import MicrostructurePaperFillProvider, PaperFillModelConfig
from execution.risk_aware_router import RiskAwareRouter
from execution.smart_router import OrderRequest, OrderType, SmartOrderRouter
from risk.kill_switches import RiskLimits


def _strategy_inputs() -> tuple[dict, list[float]]:
    strategy_returns = {
        "s1": np.linspace(-0.01, 0.01, 30),
        "s2": np.cos(np.linspace(0.0, 2.0 * np.pi, 30)) * 0.005,
    }
    portfolio_changes = np.linspace(-50.0, 50.0, 30)
    return strategy_returns, list(portfolio_changes)


def _portfolio_snapshot() -> dict:
    return {
        "positions": {"BTC": 0.25},
        "prices": {"BTC": 50000.0},
        "total_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "realized_pnl": 0.0,
        "gross_exposure": 12500.0,
        "net_exposure": 12500.0,
        "leverage": 0.25,
        "open_orders": [],
    }


def test_paper_fill_provider_is_deterministic_with_partial_fills():
    provider = MicrostructurePaperFillProvider(
        config=PaperFillModelConfig(
            partial_fill_notional_usd=1000.0,
            min_partial_fill_ratio=0.5,
            hard_reject_notional_usd=20000.0,
        )
    )

    fill_1 = asyncio.run(
        provider.get_fill(
            order_id="ord_1",
            symbol="BTC-USD",
            venue="binance",
            side="buy",
            requested_qty=1.0,
            reference_price=5000.0,
        )
    )
    fill_2 = asyncio.run(
        provider.get_fill(
            order_id="ord_1",
            symbol="BTC-USD",
            venue="binance",
            side="buy",
            requested_qty=1.0,
            reference_price=5000.0,
        )
    )

    assert fill_1.executed_qty < 1.0
    assert fill_1.executed_qty == fill_2.executed_qty
    assert fill_1.executed_price == fill_2.executed_price


def test_paper_fill_provider_hard_rejects_extreme_notional():
    provider = MicrostructurePaperFillProvider(
        config=PaperFillModelConfig(
            hard_reject_notional_usd=1000.0,
        )
    )

    fill = asyncio.run(
        provider.get_fill(
            order_id="ord_reject",
            symbol="BTC-USD",
            venue="binance",
            side="buy",
            requested_qty=1.0,
            reference_price=5000.0,
        )
    )

    assert fill.executed_qty == 0.0


def test_router_rejects_order_when_fill_provider_returns_no_fill(tmp_path):
    fill_provider = MicrostructurePaperFillProvider(
        config=PaperFillModelConfig(hard_reject_notional_usd=100.0)
    )
    router = RiskAwareRouter(
        risk_config=RiskLimits(
            max_daily_loss_pct=0.02,
            max_drawdown_pct=0.2,
            max_gross_leverage=2.0,
        ),
        broker_config={"enabled": True},
        fill_provider=fill_provider,
        tca_db_path=str(tmp_path / "no_fill.csv"),
    )
    router.set_capital(100000.0, source="unit_test")

    order = OrderRequest(
        symbol="BTC-USD",
        side="buy",
        quantity=1.0,
        order_type=OrderType.LIMIT,
        price=500.0,
    )
    market_data = {
        "binance": {
            "BTC-USD": {
                "price": 500.0,
                "spread": 0.0002,
                "volume_24h": 2_000_000,
            }
        },
        "order_book": {
            "bids": [(499.9, 20.0), (499.8, 40.0)],
            "asks": [(500.1, 15.0), (500.2, 30.0)],
        },
    }

    strategy_returns, portfolio_changes = _strategy_inputs()
    result = asyncio.run(
        router.submit_order(
            order=order,
            market_data=market_data,
            portfolio=_portfolio_snapshot(),
            strategy_returns=strategy_returns,
            portfolio_changes=portfolio_changes,
        )
    )

    assert result.success is False
    assert "NO_FILL" in (result.rejected_reason or "")


def test_router_blocks_degraded_venue_when_no_failover(tmp_path):
    router = RiskAwareRouter(
        risk_config=RiskLimits(
            max_daily_loss_pct=0.02,
            max_drawdown_pct=0.2,
            max_gross_leverage=2.0,
        ),
        broker_config={"enabled": True},
        tca_db_path=str(tmp_path / "degraded.csv"),
    )
    router.set_capital(100000.0, source="unit_test")

    for _ in range(30):
        router.reliability_monitor.record(
            venue="binance",
            latency_ms=1000.0,
            rejected=True,
            failed=True,
        )

    order = OrderRequest(
        symbol="BTC-USD",
        side="buy",
        quantity=0.2,
        order_type=OrderType.LIMIT,
        price=50000.0,
    )
    market_data = {
        "binance": {
            "BTC-USD": {
                "price": 50000.0,
                "spread": 0.0002,
                "volume_24h": 2_000_000,
            }
        },
        "order_book": {
            "bids": [(49990.0, 2.0), (49980.0, 4.0)],
            "asks": [(50010.0, 1.5), (50020.0, 3.0)],
        },
    }
    strategy_returns, portfolio_changes = _strategy_inputs()

    result = asyncio.run(
        router.submit_order(
            order=order,
            market_data=market_data,
            portfolio=_portfolio_snapshot(),
            strategy_returns=strategy_returns,
            portfolio_changes=portfolio_changes,
        )
    )

    assert result.success is False
    assert "DEGRADED_VENUE_NO_FAILOVER" in (result.rejected_reason or "")


def test_smart_router_tracks_monthly_volume_and_slippage_guard():
    router = SmartOrderRouter(
        {
            "enabled": True,
            "slippage_guard_ratio": 1.5,
            "monthly_volume_by_venue": {"binance": 1000.0},
        }
    )
    router.venue_quality["binance"] = {
        "slippage_ratio": 2.0,
        "fill_ratio": 1.0,
        "latency_ms": 20.0,
    }

    request = OrderRequest(
        symbol="BTC-USD",
        side="buy",
        quantity=0.1,
        order_type=OrderType.MARKET,
        price=None,
        time_in_force="GTC",
    )
    decision = asyncio.run(
        router.route_order(
            request,
            {
                "binance": {
                    "BTC-USD": {
                        "price": 50000.0,
                        "spread": 0.0002,
                        "volume_24h": 1_500_000,
                    }
                }
            },
        )
    )

    assert decision.order_type == OrderType.LIMIT

    router.record_executed_notional(
        "binance", 500.0, timestamp=datetime(2026, 3, 5, tzinfo=timezone.utc)
    )
    assert router.get_monthly_volume("binance") == 1500.0

    router.record_executed_notional(
        "binance", 200.0, timestamp=datetime(2026, 4, 1, tzinfo=timezone.utc)
    )
    assert router.get_monthly_volume("binance") == 1200.0


def test_engine_builds_microstructure_paper_fill_provider(tmp_path):
    config = {
        "mode": "paper_trading",
        "markets": {
            "crypto": {"enabled": True, "exchanges": [{"name": "binance", "symbols": ["BTC-USD"]}]}
        },
        "risk": {
            "initial_capital": 100000.0,
            "max_portfolio_risk_pct": 2.0,
            "max_drawdown_pct": 10.0,
            "max_leverage": 3.0,
        },
        "execution": {
            "paper_fill_model": {
                "enabled": True,
                "partial_fill_notional_usd": 1000.0,
                "hard_reject_notional_usd": 50000.0,
            }
        },
    }
    config_path = tmp_path / "engine_config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    engine = TradingEngine(str(config_path))
    router = engine._build_router()

    assert isinstance(router.fill_provider, MicrostructurePaperFillProvider)
