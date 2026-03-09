"""Tests for VPIN-style informed-flow and quote/size kill-switch actions."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.persistence import EventPersistenceStore
from execution.informed_flow_kill_switch import InformedFlowKillSwitch


def _order_book(*, bid: float = 99.99, ask: float = 100.01, bid_size: float = 800, ask_size: float = 800):
    return {
        "bids": [(bid, bid_size), (bid - 0.02, bid_size * 1.1)],
        "asks": [(ask, ask_size), (ask + 0.02, ask_size * 1.1)],
    }


def test_halt_quotes_when_vpin_extreme() -> None:
    engine = InformedFlowKillSwitch(
        lookback_trades=50,
        bucket_volume=10.0,
        vpin_reduce_threshold=0.55,
        vpin_halt_threshold=0.75,
    )
    trades = [{"side": "buy", "qty": 5.0} for _ in range(40)]  # one-sided flow
    decision = engine.evaluate(
        market_id="BTC-YES",
        order_book=_order_book(),
        reference_price=100.0,
        side="buy",
        requested_qty=5.0,
        trades=trades,
        queue_ahead_qty=0.0,
    )
    assert decision.action == "halt_quotes"
    assert decision.quote_enabled is False
    assert decision.size_multiplier == 0.0
    assert "vpin" in decision.reason


def test_reduce_size_when_liquidity_stressed() -> None:
    engine = InformedFlowKillSwitch(
        lookback_trades=40,
        bucket_volume=20.0,
        spread_reduce_bps=12.0,
        spread_halt_bps=80.0,
        vpin_reduce_threshold=0.50,
        vpin_halt_threshold=0.95,
        max_depth_participation_reduce=0.05,
        max_depth_participation_halt=0.30,
    )
    trades = ([{"side": "buy", "qty": 6.0}] * 12) + ([{"side": "sell", "qty": 4.0}] * 8)
    decision = engine.evaluate(
        market_id="ETH-NO",
        order_book=_order_book(bid=99.90, ask=100.10, bid_size=80, ask_size=80),
        reference_price=100.0,
        side="buy",
        requested_qty=10.0,
        trades=trades,
        queue_ahead_qty=4.0,
    )
    assert decision.action == "reduce_size"
    assert decision.quote_enabled is True
    assert 0.0 < decision.size_multiplier < 1.0
    assert "spread" in decision.reason or "depth participation" in decision.reason


def test_allow_and_persist_decisions(tmp_path: Path) -> None:
    store = EventPersistenceStore(dsn=f"sqlite:///{tmp_path}/events.db")
    engine = InformedFlowKillSwitch(
        persistence_store=store,
        lookback_trades=30,
        bucket_volume=30.0,
    )
    trades = [{"side": "buy", "qty": 5.0}, {"side": "sell", "qty": 5.0}] * 10
    decision = engine.evaluate(
        market_id="POLY-1",
        order_book=_order_book(bid=99.995, ask=100.005, bid_size=3000, ask_size=3000),
        reference_price=100.0,
        side="buy",
        requested_qty=1.0,
        trades=trades,
        queue_ahead_qty=1.0,
    )
    assert decision.action == "allow"
    assert decision.size_multiplier == 1.0

    replayed = engine.replay_decisions(market_id="POLY-1")
    assert len(replayed) == 1
    assert replayed[0].action == "allow"
