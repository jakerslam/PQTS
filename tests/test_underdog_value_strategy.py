from strategies.underdog_value import (
    CalibrationMetrics,
    QuoteSnapshot,
    UnderdogValueConfig,
    UnderdogValueStrategy,
)


def test_probability_normalization() -> None:
    snapshot = QuoteSnapshot(
        market_id="mkt_1",
        outcome_id="yes",
        yes_price=0.42,
        no_price=0.68,
        timestamp_ms=1_000,
        venue="test",
        depth=200.0,
    )
    strategy = UnderdogValueStrategy()
    p_market = strategy.normalize_market_probability(snapshot)
    assert 0.0 < p_market < 1.0
    assert round(p_market, 6) == round(0.42 / 1.10, 6)


def test_calibration_gate_and_signal_acceptance() -> None:
    strategy = UnderdogValueStrategy(
        UnderdogValueConfig(
            min_edge=0.02,
            min_net_ev=0.0,
            fee_bps=2.0,
            slippage_bps=1.0,
            min_depth=50.0,
        )
    )
    metrics = CalibrationMetrics(brier_score=0.15, calibration_error=0.04, sample_size=400)
    assert strategy.classify_calibration(metrics)
    snapshot = QuoteSnapshot(
        market_id="mkt_2",
        outcome_id="yes",
        yes_price=0.35,
        no_price=0.70,
        timestamp_ms=1_000,
        venue="test",
        depth=120.0,
    )
    decision = strategy.evaluate_signal(snapshot, p_model=0.42)
    assert decision.allowed
    assert decision.reason == "accepted"
    assert decision.net_ev > 0.0


def test_signal_rejected_when_not_underdog() -> None:
    strategy = UnderdogValueStrategy()
    snapshot = QuoteSnapshot(
        market_id="mkt_3",
        outcome_id="yes",
        yes_price=0.80,
        no_price=0.25,
        timestamp_ms=1_000,
        venue="test",
        depth=200.0,
    )
    decision = strategy.evaluate_signal(snapshot, p_model=0.81)
    assert not decision.allowed
    assert decision.reason == "not_underdog"


def test_position_sizing_and_edge_disable() -> None:
    strategy = UnderdogValueStrategy(UnderdogValueConfig(kelly_fraction=0.5, max_position_fraction=0.02))
    snapshot = QuoteSnapshot(
        market_id="mkt_4",
        outcome_id="yes",
        yes_price=0.40,
        no_price=0.65,
        timestamp_ms=1_000,
        venue="test",
        depth=200.0,
    )
    decision = strategy.evaluate_signal(snapshot, p_model=0.47)
    sizing = strategy.size_position(
        decision=decision,
        payout_multiple=1.5,
        event_exposure=0.0,
        strategy_exposure=0.0,
        rolling_realized_edge=0.01,
    )
    assert not sizing.blocked
    assert 0.0 < sizing.approved_fraction <= 0.02

    blocked = strategy.size_position(
        decision=decision,
        payout_multiple=1.5,
        event_exposure=0.0,
        strategy_exposure=0.0,
        rolling_realized_edge=-0.02,
    )
    assert blocked.blocked
    assert blocked.reason == "rolling_edge_disable"


def test_exit_policy_and_telemetry_diagnostics() -> None:
    strategy = UnderdogValueStrategy()
    mode = strategy.choose_exit_mode(mark_probability=0.51, fair_probability=0.50)
    assert mode == "fair_value_convergence"

    snapshot = QuoteSnapshot(
        market_id="mkt_5",
        outcome_id="yes",
        yes_price=0.40,
        no_price=0.70,
        timestamp_ms=2_000,
        venue="test",
        depth=200.0,
    )
    decision = strategy.evaluate_signal(snapshot, p_model=0.46)
    telemetry = strategy.signal_telemetry(snapshot, decision=decision, expected_ev=decision.net_ev)
    assert telemetry["market_id"] == "mkt_5"
    assert "edge" in telemetry
    diagnostics = strategy.realized_vs_expected_diagnostics(realized_ev=0.015, expected_ev=0.01)
    assert abs(diagnostics["delta_ev"] - 0.005) < 1e-12
