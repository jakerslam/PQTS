"""Tests for orderbook sequence gap detection and recovery."""

from __future__ import annotations

from execution.orderbook_sequence import OrderBookSequenceTracker


def test_sequence_tracker_accepts_seed_and_in_order_updates() -> None:
    tracker = OrderBookSequenceTracker()
    seed = tracker.process_update(stream_id="binance:BTCUSDT", sequence=100)
    assert seed.mode == "seed"
    assert tracker.expected_next("binance:BTCUSDT") == 101

    in_order = tracker.process_update(stream_id="binance:BTCUSDT", sequence=101)
    assert in_order.mode == "in_order"
    assert tracker.expected_next("binance:BTCUSDT") == 102


def test_sequence_tracker_detects_gap_and_recovers_via_snapshot() -> None:
    tracker = OrderBookSequenceTracker(allow_auto_recover=True)
    _ = tracker.process_update(stream_id="coinbase:ETHUSD", sequence=500)
    event = tracker.process_update(
        stream_id="coinbase:ETHUSD",
        sequence=504,
        snapshot_sequence=600,
    )
    assert event.mode == "gap_recovered_snapshot"
    assert event.gap_size == 3
    assert event.recovered is True
    assert tracker.expected_next("coinbase:ETHUSD") == 601
    assert tracker.has_open_gap("coinbase:ETHUSD") is False


def test_sequence_tracker_keeps_gap_open_without_snapshot_recovery() -> None:
    tracker = OrderBookSequenceTracker(allow_auto_recover=False)
    _ = tracker.process_update(stream_id="kraken:SOLUSD", sequence=10)
    event = tracker.process_update(stream_id="kraken:SOLUSD", sequence=13)
    assert event.mode == "gap_detected"
    assert event.gap_size == 2
    assert tracker.has_open_gap("kraken:SOLUSD") is True

    sync = tracker.apply_snapshot(stream_id="kraken:SOLUSD", snapshot_sequence=20)
    assert sync.mode == "snapshot_sync"
    assert tracker.expected_next("kraken:SOLUSD") == 21
