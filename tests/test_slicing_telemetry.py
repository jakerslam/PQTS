"""Tests for execution slicing and fill-quality telemetry."""

from __future__ import annotations

from datetime import datetime, timezone

from execution.slicing_telemetry import ExecutionQualityTelemetry, ExecutionSlicer


def test_twap_vwap_and_depth_aware_slice_plans() -> None:
    slicer = ExecutionSlicer(max_participation=0.10, default_slice_delay_seconds=5.0)

    twap = slicer.plan_twap(order_id="ord_twap", quantity=10.0, intervals=4)
    assert len(twap) == 4
    assert abs(sum(item.quantity for item in twap) - 10.0) < 1e-9
    assert all(item.mode == "twap" for item in twap)

    vwap = slicer.plan_vwap(order_id="ord_vwap", quantity=10.0, volume_profile=[1.0, 2.0, 1.0])
    assert len(vwap) == 3
    assert vwap[1].quantity > vwap[0].quantity
    assert abs(sum(item.quantity for item in vwap) - 10.0) < 1e-9

    depth = slicer.plan_depth_aware(order_id="ord_depth", quantity=10.0, depth_quantity=20.0)
    assert len(depth) == 5  # max slice = 2.0 under 10% participation
    assert all(item.mode == "depth_aware" for item in depth)


def test_execution_quality_reports_slippage_and_time_to_fill() -> None:
    telemetry = ExecutionQualityTelemetry()
    start = datetime(2026, 3, 9, 0, 0, tzinfo=timezone.utc)
    telemetry.start_order("ord1", timestamp=start)
    telemetry.record_fill(
        order_id="ord1",
        quantity=1.0,
        expected_price=100.0,
        fill_price=100.2,
        timestamp=datetime(2026, 3, 9, 0, 0, 5, tzinfo=timezone.utc),
    )
    telemetry.record_fill(
        order_id="ord1",
        quantity=1.0,
        expected_price=100.0,
        fill_price=100.1,
        timestamp=datetime(2026, 3, 9, 0, 0, 8, tzinfo=timezone.utc),
    )
    summary = telemetry.summarize("ord1", target_quantity=2.0)
    assert summary.filled_quantity == 2.0
    assert summary.fill_ratio == 1.0
    assert summary.time_to_fill_seconds == 8.0
    assert summary.slippage_bps > 0.0
