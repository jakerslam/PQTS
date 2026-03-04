"""Tests for control-plane usage metering and pricing recommendations."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analytics.control_plane import ControlPlaneMeter, pricing_tier_recommendation


def test_control_plane_usage_summary_and_arr_estimate(tmp_path):
    meter = ControlPlaneMeter(log_path=str(tmp_path / "usage.jsonl"))
    now = datetime.now(timezone.utc).isoformat()

    meter.emit(
        tenant_id="tenant_a",
        event_type="backtest_run",
        units=1000.0,
        revenue_hint_usd=999.0,
        timestamp=now,
    )
    meter.emit(
        tenant_id="tenant_b",
        event_type="risk_report",
        units=100.0,
        revenue_hint_usd=599.0,
        timestamp=now,
    )

    summary = meter.usage_summary(window_days=30)

    assert summary["summary"]["tenant_count"] == 2
    assert summary["summary"]["events"] == 2
    assert summary["summary"]["mrr_estimate_usd"] == 1598.0
    assert summary["summary"]["arr_estimate_usd"] == 19176.0


def test_pricing_tier_recommendation_thresholds():
    assert pricing_tier_recommendation(total_units=1000.0, monthly_events=200)["tier"] == "starter"
    assert pricing_tier_recommendation(total_units=50000.0, monthly_events=1000)["tier"] == "pro"
    assert (
        pricing_tier_recommendation(total_units=200000.0, monthly_events=50000)["tier"]
        == "enterprise"
    )
