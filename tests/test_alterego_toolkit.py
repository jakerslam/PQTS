from __future__ import annotations

from execution.alterego_toolkit import (
    IndicatorProviderManifest,
    RecorderSourcePoint,
    build_fast_action_intent_receipt,
    build_recorder_sync_artifact,
    evaluate_indicator_feed,
    evaluate_near_close_guard,
    segment_wallet_history,
)


def test_fast_action_receipt_blocks_bypass_attempt() -> None:
    receipt = build_fast_action_intent_receipt(
        intent_id="intent-1",
        trigger_source="hotkey",
        router_gate_passed=True,
        risk_gate_passed=True,
        bypass_attempted=True,
    )
    assert receipt.disposition == "blocked"
    assert "bypass_attempt_blocked" in receipt.reason_codes


def test_recorder_sync_artifact_reports_drift() -> None:
    artifact = build_recorder_sync_artifact(
        timeline_id="tl-1",
        points=[
            RecorderSourcePoint(source_id="pm", source_kind="prediction", sequence=1, timestamp_ms=1000),
            RecorderSourcePoint(source_id="ref", source_kind="reference", sequence=1, timestamp_ms=1400),
        ],
        max_drift_ms=200,
    )
    assert artifact.quality_ok is False
    assert "sync_drift_exceeded" in artifact.reason_codes


def test_near_close_guard_blocks_bad_quality_inputs() -> None:
    decision = evaluate_near_close_guard(
        now_ts="2026-03-20T12:00:00+00:00",
        close_ts="2026-03-20T12:04:00+00:00",
        stale_price_age_ms=5000,
        estimated_impact_bps=15.0,
        settlement_uncertainty=0.35,
        max_entry_window_seconds=600,
        max_stale_price_age_ms=1000,
        max_impact_bps=10.0,
        max_settlement_uncertainty=0.20,
    )
    assert decision.allow_entry is False
    assert "impact_exceeded" in decision.reason_codes


def test_wallet_segmentation_marks_advisory_only() -> None:
    segments = segment_wallet_history(
        [
            {"market_id": "m1", "quantity_delta": 2.0, "provenance_confidence": 0.9},
            {"market_id": "m1", "quantity_delta": -1.0, "provenance_confidence": 0.8},
        ]
    )
    assert len(segments) == 2
    assert segments[0].action == "accumulation"
    assert segments[1].action == "deaccumulation"
    assert all(row.advisory_only for row in segments)


def test_indicator_feed_downgrades_when_stale_and_low_lift() -> None:
    manifest = IndicatorProviderManifest(
        provider_id="provider-a",
        entitlement_scope="read",
        latency_ms=30,
        update_cadence_seconds=60,
        failure_modes=("lag",),
        cost_model="tiered",
    )
    decision = evaluate_indicator_feed(
        manifest=manifest,
        as_of_ts="2026-03-20T12:00:00+00:00",
        now_ts="2026-03-20T12:10:00+00:00",
        max_freshness_ms=120000,
        ablation_lift_bps=0.5,
        min_ablation_lift_bps=2.0,
    )
    assert decision.action in {"shadow_only", "review"}
    assert "indicator_feed_stale" in decision.reason_codes
