from __future__ import annotations

from contracts.execution_flow import ExecutionOutcome, OrderIntent, RoutePreview


def test_order_intent_to_dict_has_iso_timestamp() -> None:
    payload = OrderIntent(
        order_id="ord_1",
        strategy_id="strat_a",
        symbol="BTC/USD",
        side="buy",
        quantity=1.25,
        order_type="limit",
        requested_price=50000.0,
        expected_alpha_bps=12.0,
    ).to_dict()
    assert payload["order_id"] == "ord_1"
    assert payload["strategy_id"] == "strat_a"
    assert payload["source"] == "strategy"
    assert payload["mode"] == "paper_autopilot"
    assert "created_at" in payload
    assert "T" in payload["created_at"]


def test_order_intent_from_dict_roundtrip_keeps_control_fields() -> None:
    payload = {
        "order_id": "ord_2",
        "strategy_id": "manual_trade",
        "symbol": "ETH-USD",
        "side": "sell",
        "quantity": 2.0,
        "order_type": "market",
        "requested_price": 3000.0,
        "expected_alpha_bps": 0.0,
        "source": "human",
        "mode": "assisted_manual",
        "approval_status": "approved",
        "reduce_only": True,
    }
    intent = OrderIntent.from_dict(payload)
    assert intent.source == "human"
    assert intent.mode == "assisted_manual"
    assert intent.approval_status == "approved"
    assert intent.reduce_only is True


def test_route_preview_to_dict_roundtrip() -> None:
    payload = RoutePreview(
        venue="binance",
        ranked_venues=["binance", "coinbase"],
        order_type="limit",
        expected_cost_usd=1.2,
        expected_slippage_usd=0.8,
        predicted_total_router_bps=2.0,
        predicted_net_alpha_bps=5.0,
    ).to_dict()
    assert payload["venue"] == "binance"
    assert payload["ranked_venues"] == ["binance", "coinbase"]
    assert payload["predicted_net_alpha_bps"] == 5.0


def test_execution_outcome_to_dict_has_iso_timestamp() -> None:
    payload = ExecutionOutcome(
        success=False,
        decision="halt",
        order_id=None,
        venue="binance",
        rejected_reason="RISK_LIMIT",
        latency_ms=12.4,
        fill_ratio=0.0,
    ).to_dict()
    assert payload["success"] is False
    assert payload["decision"] == "halt"
    assert payload["rejected_reason"] == "RISK_LIMIT"
    assert payload["latency_ms"] == 12.4
    assert "created_at" in payload
