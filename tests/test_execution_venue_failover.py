"""Tests for venue failover policy selection."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from execution.venue_failover import select_primary_and_fallback  # noqa: E402


def test_failover_selects_best_primary_and_fallback() -> None:
    report = select_primary_and_fallback(
        [
            {"venue": "binance", "latency_ms": 32, "reject_rate": 0.01, "connected": True, "liquidity_score": 0.95},
            {"venue": "coinbase", "latency_ms": 48, "reject_rate": 0.02, "connected": True, "liquidity_score": 0.90},
            {"venue": "oanda", "latency_ms": 410, "reject_rate": 0.01, "connected": True, "liquidity_score": 0.80},
        ]
    )
    assert report["primary"]["venue"] == "binance"
    assert report["fallback"]["venue"] == "coinbase"
    assert report["failover_ready"] is True


def test_failover_reports_not_ready_when_single_eligible_venue() -> None:
    report = select_primary_and_fallback(
        [
            {"venue": "binance", "latency_ms": 30, "reject_rate": 0.01, "connected": True, "liquidity_score": 0.95},
            {"venue": "coinbase", "latency_ms": 999, "reject_rate": 0.5, "connected": True, "liquidity_score": 0.9},
        ]
    )
    assert report["primary"]["venue"] == "binance"
    assert report["fallback"] is None
    assert report["failover_ready"] is False
