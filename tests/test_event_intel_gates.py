from __future__ import annotations

from execution.event_intel_gates import evaluate_event_intel_candidate


def _records() -> list[dict[str, object]]:
    return [
        {"source": "news_a", "event_ts": "2026-03-11T12:00:00+00:00"},
        {"source": "news_b", "event_ts": "2026-03-11T12:00:20+00:00"},
    ]


def test_event_intel_candidate_allows_when_corroborated_and_causal() -> None:
    decision = evaluate_event_intel_candidate(
        records=_records(),
        quote_ts="2026-03-11T12:00:30+00:00",
        now_ts="2026-03-11T12:00:35+00:00",
        min_sources=2,
        max_skew_seconds=60.0,
    )
    assert decision.allow is True
    assert decision.decision == "ALLOW"
    assert decision.reason_codes == []


def test_event_intel_candidate_blocks_on_insufficient_sources() -> None:
    decision = evaluate_event_intel_candidate(
        records=[{"source": "news_a", "event_ts": "2026-03-11T12:00:00+00:00"}],
        quote_ts="2026-03-11T12:00:30+00:00",
        now_ts="2026-03-11T12:00:35+00:00",
        min_sources=2,
    )
    assert decision.allow is False
    assert "insufficient_records" in decision.reason_codes


def test_event_intel_candidate_blocks_on_lookahead_violation() -> None:
    decision = evaluate_event_intel_candidate(
        records=_records(),
        quote_ts="2026-03-11T12:00:10+00:00",
        now_ts="2026-03-11T12:00:12+00:00",
        min_sources=2,
        max_clock_skew_seconds=1.0,
    )
    assert decision.allow is False
    assert "lookahead_violation" in decision.reason_codes
