from analytics.readiness_gates import (
    evaluate_backtest_readiness,
    evaluate_paper_trade_readiness,
    evaluate_promotion_gate,
)


def test_backtest_readiness_passes() -> None:
    result = evaluate_backtest_readiness(
        net_expectancy=0.03,
        calibration_stability=0.90,
        max_drawdown_observed=0.12,
    )
    assert result.passed
    assert result.reasons == ()


def test_backtest_readiness_fails_with_reasons() -> None:
    result = evaluate_backtest_readiness(
        net_expectancy=-0.01,
        calibration_stability=0.70,
        max_drawdown_observed=0.35,
    )
    assert not result.passed
    assert "expectancy_not_positive" in result.reasons
    assert "calibration_unstable" in result.reasons
    assert "drawdown_exceeds_tolerance" in result.reasons


def test_paper_trade_readiness_contract() -> None:
    ok = evaluate_paper_trade_readiness(
        realized_net_alpha=0.02,
        sample_size=200,
        critical_violations=0,
        slippage_mape=0.10,
    )
    assert ok.passed

    bad = evaluate_paper_trade_readiness(
        realized_net_alpha=-0.01,
        sample_size=30,
        critical_violations=1,
        slippage_mape=0.40,
    )
    assert not bad.passed
    assert len(bad.reasons) == 4


def test_promotion_gate_contract() -> None:
    ok = evaluate_promotion_gate(
        paper_campaign_passed=True,
        unresolved_high_severity_incidents=0,
        stress_replay_passed=True,
        portfolio_limits_intact=True,
    )
    assert ok.passed

    bad = evaluate_promotion_gate(
        paper_campaign_passed=False,
        unresolved_high_severity_incidents=2,
        stress_replay_passed=False,
        portfolio_limits_intact=False,
    )
    assert not bad.passed
    assert "paper_campaign_not_passed" in bad.reasons
