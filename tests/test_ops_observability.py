"""Tests for ops observability event logging and alerts."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analytics.ops_observability import OpsEventStore, build_ops_alerts


def test_ops_event_store_emit_read_and_summary(tmp_path):
    path = tmp_path / "ops_events.jsonl"
    store = OpsEventStore(str(path))
    store.emit(
        category="execution",
        severity="warning",
        message="high_reject_rate",
        metrics={"reject_rate": 0.30},
    )
    store.emit(
        category="autopilot",
        severity="info",
        message="selection_applied",
    )
    rows = store.read_events()
    summary = store.summarize()

    assert len(rows) == 2
    assert summary["events"] == 2
    assert summary["by_category"]["execution"] == 1
    assert summary["by_severity"]["warning"] == 1


def test_build_ops_alerts_flags_threshold_breaches():
    alerts = build_ops_alerts(
        rows=[
            {"metrics": {"reject_rate": 0.4}},
            {"metrics": {"slippage_mape_pct": 50.0}},
        ],
        max_reject_rate=0.2,
        max_slippage_mape_pct=35.0,
    )
    assert len(alerts) == 2
