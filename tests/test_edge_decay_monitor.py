from __future__ import annotations

from risk.edge_decay_monitor import EdgeDecayMonitor


def test_edge_decay_monitor_holds_without_enough_samples() -> None:
    monitor = EdgeDecayMonitor(min_samples_per_bucket=3)
    monitor.record(latency_ms=30, concurrent_load=2, realized_edge_bps=1.2)
    decision = monitor.decision()
    assert decision["action"] == "hold"
    assert decision["reason"] == "insufficient_samples"


def test_edge_decay_monitor_tightens_on_medium_decay() -> None:
    monitor = EdgeDecayMonitor(min_samples_per_bucket=3, decay_tighten_threshold=0.3, decay_pause_threshold=0.7)
    for value in [2.0, 2.2, 1.9]:
        monitor.record(latency_ms=20, concurrent_load=3, realized_edge_bps=value)
    for value in [1.2, 1.1, 1.0]:
        monitor.record(latency_ms=90, concurrent_load=25, realized_edge_bps=value)
    decision = monitor.decision()
    assert decision["action"] == "tighten"
    assert 0.3 <= decision["decay_pct"] < 0.7


def test_edge_decay_monitor_pauses_on_severe_decay() -> None:
    monitor = EdgeDecayMonitor(min_samples_per_bucket=3, decay_tighten_threshold=0.2, decay_pause_threshold=0.5)
    for value in [2.0, 2.1, 2.2]:
        monitor.record(latency_ms=10, concurrent_load=1, realized_edge_bps=value)
    for value in [0.5, 0.4, 0.3]:
        monitor.record(latency_ms=150, concurrent_load=30, realized_edge_bps=value)
    decision = monitor.decision()
    assert decision["action"] == "pause"
    assert decision["recommended_concurrency_scale"] == 0.0
