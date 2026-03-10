from analytics.hft_path_monitor import HFTPathMonitor, HFTSLOBudget
from execution.analysis_execution_contract import AnalysisPayload, analysis_to_execution


def test_analysis_execution_contract_validates_and_converts() -> None:
    payload = AnalysisPayload(
        schema_version=1,
        decision_id="d1",
        strategy_id="short_cycle",
        asset="BTC",
        interval="5m",
        generated_at_ms=1_000,
        factors={
            "price_vs_target": 0.2,
            "momentum": 0.3,
            "volatility": -0.1,
            "contract_mispricing": 0.4,
            "futures_sentiment": 0.1,
            "time_decay": 0.05,
        },
        confidence=0.8,
        requested_kelly_fraction=0.2,
    )
    valid, instruction, errors = analysis_to_execution(payload, now_ms=1_500)
    assert valid
    assert errors == ()
    assert instruction is not None
    assert instruction["decision_id"] == "d1"


def test_analysis_execution_contract_fails_closed_for_stale_or_invalid_payload() -> None:
    stale_payload = AnalysisPayload(
        schema_version=1,
        decision_id="d2",
        strategy_id="short_cycle",
        asset="BTC",
        interval="5m",
        generated_at_ms=1_000,
        factors={"price_vs_target": 0.1},  # intentionally incomplete
        confidence=1.2,
        requested_kelly_fraction=1.2,
    )
    valid, instruction, errors = analysis_to_execution(stale_payload, now_ms=5_000, max_age_ms=500)
    assert not valid
    assert instruction is None
    assert any(item.startswith("missing_factors:") for item in errors)
    assert "stale_payload" in errors


def test_hft_monitor_slo_and_governance() -> None:
    monitor = HFTPathMonitor(
        HFTSLOBudget(
            p95_submit_to_ack_ms=50.0,
            p99_submit_to_ack_ms=80.0,
            max_reject_rate=0.10,
            max_timeout_rate=0.05,
            max_decision_to_submit_ms=20.0,
            max_orders_per_minute=2,
            max_cancel_replace_per_minute=1,
        )
    )
    monitor.record(
        submit_to_ack_ms=30.0,
        decision_to_submit_ms=10.0,
        rejected=False,
        timeout=False,
        timestamp_ms=1_000,
        cancel_replace=False,
    )
    monitor.record(
        submit_to_ack_ms=95.0,
        decision_to_submit_ms=25.0,
        rejected=True,
        timeout=False,
        timestamp_ms=1_100,
        cancel_replace=True,
    )
    monitor.record(
        submit_to_ack_ms=110.0,
        decision_to_submit_ms=30.0,
        rejected=False,
        timeout=True,
        timestamp_ms=1_200,
        cancel_replace=True,
    )

    summary = monitor.summary()
    assert summary["p95_submit_to_ack_ms"] >= 95.0
    healthy, reasons = monitor.should_auto_disable()
    assert not healthy
    assert "p95_submit_to_ack_slo_breach" in reasons
    assert "orders_per_minute_breach" in reasons
