"""Tests for cross-venue dislocation detection and hedged routing plan."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.persistence import EventPersistenceStore
from execution.cross_venue_dislocation import CrossVenueDislocationPlanner


def test_detects_actionable_dislocation() -> None:
    planner = CrossVenueDislocationPlanner(
        min_net_edge_bps=5.0,
        default_fee_bps=1.0,
        slippage_buffer_bps=1.0,
    )
    quotes = {
        "venue_a": {"bid": 99.8, "ask": 100.0, "bid_depth": 2000, "ask_depth": 2000},
        "venue_b": {"bid": 100.25, "ask": 100.35, "bid_depth": 1800, "ask_depth": 1800},
    }
    plan = planner.plan(symbol="BTC-YES", venue_quotes=quotes)
    assert plan.enabled is True
    assert plan.selected is not None
    assert plan.selected.buy_venue == "venue_a"
    assert plan.selected.sell_venue == "venue_b"
    assert plan.selected.net_edge_bps > 5.0


def test_dislocation_below_threshold_is_not_enabled() -> None:
    planner = CrossVenueDislocationPlanner(
        min_net_edge_bps=12.0,
        default_fee_bps=1.0,
        slippage_buffer_bps=1.0,
    )
    quotes = {
        "venue_a": {"price": 100.0, "spread": 0.04, "volume_24h": 5000},
        "venue_b": {"price": 100.14, "spread": 0.04, "volume_24h": 5000},
    }
    plan = planner.plan(symbol="ETH-NO", venue_quotes=quotes)
    assert plan.enabled is False
    assert plan.selected is None
    assert "below min threshold" in plan.reason


def test_persistence_and_replay(tmp_path: Path) -> None:
    store = EventPersistenceStore(dsn=f"sqlite:///{tmp_path}/events.db")
    planner = CrossVenueDislocationPlanner(
        min_net_edge_bps=2.0,
        default_fee_bps=0.5,
        slippage_buffer_bps=0.5,
        persistence_store=store,
    )
    quotes = {
        "x": {"bid": 10.0, "ask": 10.05, "bid_depth": 10000, "ask_depth": 10000},
        "y": {"bid": 10.12, "ask": 10.16, "bid_depth": 9000, "ask_depth": 9000},
    }
    plan = planner.plan(symbol="POLY-EDGE", venue_quotes=quotes)
    assert plan.enabled is True

    replayed = planner.replay_plans(symbol="POLY-EDGE")
    assert len(replayed) == 1
    assert replayed[0].enabled is True
