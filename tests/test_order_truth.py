from __future__ import annotations

from pathlib import Path

from execution.order_truth import (
    build_pretrade_evidence_bundle,
    load_pretrade_evidence_bundle,
    persist_pretrade_evidence_bundle,
    summarize_pretrade_evidence,
)


def test_order_truth_evidence_bundle_round_trip(tmp_path: Path) -> None:
    bundle = build_pretrade_evidence_bundle(
        candidate_id="cand-1",
        strategy_id="event_intel_alpha",
        trust_label="diagnostic_only",
        quote_ts="2026-03-11T12:00:00+00:00",
        decision_ts="2026-03-11T12:00:01+00:00",
        order_submit_ts="2026-03-11T12:00:02+00:00",
        corroboration_source_count=3,
        corroboration_skew_seconds=18.5,
        causal_ok=True,
        event_minus_quote_seconds=-0.5,
        expected_net_ev=0.018,
        risk_gate_decision="ALLOW",
        gate_reason_codes=[],
        latency_ms=190.2,
    )
    target = persist_pretrade_evidence_bundle(bundle, tmp_path / "event_intel_latest.json")
    loaded = load_pretrade_evidence_bundle(target)
    assert loaded is not None
    summary = summarize_pretrade_evidence(loaded)
    assert summary is not None
    assert summary["candidate_id"] == "cand-1"
    assert summary["source_count"] == 3
    assert summary["risk_gate_decision"] == "ALLOW"
