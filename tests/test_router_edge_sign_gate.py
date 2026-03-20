from __future__ import annotations

import asyncio

import numpy as np

from execution.risk_aware_router import RiskAwareRouter
from execution.smart_router import OrderRequest, OrderType
from risk.kill_switches import RiskLimits


def _market_data(price: float = 50000.0) -> dict:
    return {
        "binance": {
            "BTC-USD": {
                "price": price,
                "spread": 0.0002,
                "volume_24h": 2_000_000,
            }
        },
        "order_book": {
            "bids": [(price * 0.9998, 2.0), (price * 0.9996, 4.0)],
            "asks": [(price * 1.0002, 1.5), (price * 1.0004, 3.0)],
        },
    }


def _portfolio(price: float = 50000.0) -> dict:
    return {
        "positions": {"BTC": 0.25},
        "prices": {"BTC": price},
        "total_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "realized_pnl": 0.0,
        "gross_exposure": price * 0.25,
        "net_exposure": price * 0.25,
        "leverage": 0.25,
        "open_orders": [],
    }


def test_router_blocks_non_positive_edge_when_gate_enabled(tmp_path) -> None:
    router = RiskAwareRouter(
        risk_config=RiskLimits(max_daily_loss_pct=0.02, max_drawdown_pct=0.2, max_gross_leverage=2.0),
        broker_config={
            "enabled": True,
            "edge_sign_gate": {"enabled": True, "allow_override_simulation": False},
            "order_ledger_path": str(tmp_path / "ledger.jsonl"),
            "tca_db_path": str(tmp_path / "tca.csv"),
        },
        tca_db_path=str(tmp_path / "tca.csv"),
    )
    router.set_capital(100000.0, source="unit_test")

    order = OrderRequest(
        symbol="BTC-USD",
        side="buy",
        quantity=0.1,
        order_type=OrderType.LIMIT,
        price=50000.0,
        expected_alpha_bps=1.0,
        decision_context={
            "model_probability": 0.49,
            "market_probability": 0.50,
            "manual_override": True,
            "override_reason": "narrative conviction",
        },
    )

    strategy_returns = {
        "s1": np.linspace(-0.01, 0.01, 30),
        "s2": np.cos(np.linspace(0.0, 2.0 * np.pi, 30)) * 0.005,
    }
    portfolio_changes = list(np.linspace(-50.0, 50.0, 30))

    result = asyncio.run(
        router.submit_order(
            order=order,
            market_data=_market_data(),
            portfolio=_portfolio(),
            strategy_returns=strategy_returns,
            portfolio_changes=portfolio_changes,
        )
    )

    assert result.success is False
    assert result.rejected_reason is not None and "NON_POSITIVE_EDGE" in result.rejected_reason
    assert result.audit_log["edge_sign_gate"]["reason_code"] == "non_positive_edge"
