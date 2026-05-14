"""Deterministic tests for AIResearchAgent constraints and promotion gates."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.ai_agent import AIResearchAgent
from research.auto_generator import AutoStrategyGenerator, StrategyVariant
from research.database import Experiment


def _historical_data() -> dict[str, pd.DataFrame]:
    index = pd.date_range("2025-01-01", periods=360, freq="h")
    btc = (
        100.0 + np.linspace(0.0, 8.0, len(index)) + 0.8 * np.sin(np.linspace(0.0, 15.0, len(index)))
    )
    eth = (
        60.0 + np.linspace(0.0, 4.0, len(index)) + 0.5 * np.cos(np.linspace(0.0, 18.0, len(index)))
    )
    return {
        "BTCUSDT": pd.DataFrame({"close": btc}, index=index),
        "ETHUSDT": pd.DataFrame({"close": eth}, index=index),
    }


def _agent_config(tmp_path: Path) -> dict:
    return {
        "db_path": str(tmp_path / "research.db"),
        "search_budget": 12,
        "top_performers": 3,
        "min_sharpe": 0.2,
        "max_drawdown": 0.35,
        "min_profit_factor": 1.0,
        "min_deflated_sharpe": -1.0,
        "max_pbo": 1.0,
        "walk_forward": {
            "train_years": 1,
            "validate_years": 1,
            "test_years": 1,
            "step_years": 1,
        },
        "capacity": {
            "deployable_capital": 500000.0,
            "max_annual_turnover_notional": 500000000.0,
        },
        "costs": {
            "commission_bps": 6.0,
            "slippage_bps": 8.0,
            "borrow_funding_bps": 3.0,
        },
        "objective": {
            "max_sharpe": 1.5,
            "max_annual_vol": 0.25,
            "annual_turnover": 6.0,
            "cost_per_turnover": 0.0045,
            "target_annual_profit": 1000000.0,
        },
    }


def _log_paper_metrics(agent: AIResearchAgent, strategy_id: str, slippage: float = 10.0) -> None:
    now = datetime.now(timezone.utc)
    for day_offset in range(30):
        agent.record_stage_metrics(
            strategy_id,
            "paper",
            {
                "pnl": 100.0,
                "sharpe": 1.25,
                "drawdown": 0.08,
                "slippage_mape": slippage,
                "kill_switch_triggers": 0,
            },
            timestamp=now - timedelta(days=day_offset),
        )


def test_objective_constraints_block_unrealistic_10x_monthly(tmp_path):
    agent = AIResearchAgent(_agent_config(tmp_path))
    assessment = agent.validate_objective_constraints({"target_monthly_return": 10.0})

    assert assessment["objective_valid"] is False
    assert any("target_monthly_return" in msg for msg in assessment["violations"])


def test_deterministic_backtest_metrics_repeat_exactly(tmp_path):
    agent = AIResearchAgent(_agent_config(tmp_path))
    variant = StrategyVariant(
        strategy_id="market_making_fixed",
        strategy_type="market_making",
        features=["ob_imbalance", "vol_regime"],
        parameters={"spread_bps": 20, "skew_factor": 0.25},
    )
    data = _historical_data()

    first = agent._run_deterministic_backtest(variant, data)
    second = agent._run_deterministic_backtest(variant, data)

    assert np.isclose(first["sharpe"], second["sharpe"])
    assert np.isclose(first["total_return"], second["total_return"])
    assert np.isclose(first["max_drawdown"], second["max_drawdown"])
    assert first["total_trades"] == second["total_trades"]


def test_symbol_aware_momentum_can_rotate_to_stronger_asset(tmp_path):
    agent = AIResearchAgent(_agent_config(tmp_path))
    index = pd.date_range("2025-01-01", periods=240, freq="h")
    winner = 100.0 * np.exp(np.linspace(0.0, 0.30, len(index)))
    loser = 100.0 * np.exp(np.linspace(0.0, -0.20, len(index)))
    data = {
        "WIN": pd.DataFrame({"close": winner}, index=index),
        "LOSE": pd.DataFrame({"close": loser}, index=index),
    }
    variant = StrategyVariant(
        strategy_id="cross_sectional_momentum_rotation",
        strategy_type="cross_sectional_momentum",
        features=["relative_strength_24h", "vol_regime"],
        parameters={
            "lookback_periods": 12,
            "top_n": 1,
            "rebalance_periods": 6,
            "min_signal_bps": 0.0,
        },
    )

    metrics = agent._run_deterministic_backtest(variant, data)

    assert metrics["total_return"] > 0.10
    assert metrics["sharpe"] > 0.0
    assert metrics["total_trades"] > 0


def test_symbol_aware_trend_can_sit_in_cash_during_downtrend(tmp_path):
    agent = AIResearchAgent(_agent_config(tmp_path))
    index = pd.date_range("2025-01-01", periods=180, freq="h")
    falling_a = 100.0 * np.exp(np.linspace(0.0, -0.25, len(index)))
    falling_b = 80.0 * np.exp(np.linspace(0.0, -0.18, len(index)))
    data = {
        "A": pd.DataFrame({"close": falling_a}, index=index),
        "B": pd.DataFrame({"close": falling_b}, index=index),
    }
    variant = StrategyVariant(
        strategy_id="adaptive_trend_cash_filter",
        strategy_type="adaptive_trend",
        features=["price_momentum_1h", "vol_regime"],
        parameters={
            "fast_periods": 12,
            "slow_periods": 48,
            "rebalance_periods": 6,
            "min_trend_bps": 0.0,
        },
    )

    metrics = agent._run_deterministic_backtest(variant, data)

    assert metrics["max_drawdown"] <= 0.01
    assert metrics["total_return"] >= -0.01


def test_markov_regime_can_allocate_to_persistent_bull_asset(tmp_path):
    agent = AIResearchAgent(_agent_config(tmp_path))
    index = pd.date_range("2025-01-01", periods=240, freq="h")
    bull = 100.0 * np.exp(np.linspace(0.0, 0.35, len(index)))
    bear = 100.0 * np.exp(np.linspace(0.0, -0.25, len(index)))
    data = {
        "BULL": pd.DataFrame({"close": bull}, index=index),
        "BEAR": pd.DataFrame({"close": bear}, index=index),
    }
    variant = StrategyVariant(
        strategy_id="markov_regime_persistent_bull",
        strategy_type="markov_regime",
        features=["observable_regime_state", "transition_probability"],
        parameters={
            "regime_window": 6,
            "transition_lookback": 24,
            "bull_threshold_bps": 10.0,
            "bear_threshold_bps": -10.0,
            "signal_threshold": 0.01,
            "forecast_steps": 1,
            "min_row_transitions": 1,
            "smoothing": 0.1,
            "max_assets": 1,
            "rebalance_periods": 6,
        },
    )

    metrics = agent._run_deterministic_backtest(variant, data)

    assert metrics["total_return"] > 0.10
    assert metrics["sharpe"] > 0.0
    assert metrics["total_trades"] > 0


def test_stage_gate_promotes_paper_to_live_canary(tmp_path):
    agent = AIResearchAgent(_agent_config(tmp_path))
    strategy_id = "mm_gate_pass"

    agent.db.log_experiment(
        Experiment(
            experiment_id=strategy_id,
            strategy_name="market_making",
            variant_id="gate_pass",
            features=["ob_imbalance"],
            parameters={},
            status="paper",
        )
    )
    _log_paper_metrics(agent, strategy_id, slippage=12.0)

    assessment = agent.evaluate_stage_gate(strategy_id, "live_canary")
    assert assessment["passed"] is True
    assert agent.promote_from_stage(strategy_id, "live_canary") is True
    assert agent.db.get_experiment_status(strategy_id) == "live_canary"


def test_stage_gate_blocks_on_slippage_drift(tmp_path):
    agent = AIResearchAgent(_agent_config(tmp_path))
    strategy_id = "mm_gate_block"

    agent.db.log_experiment(
        Experiment(
            experiment_id=strategy_id,
            strategy_name="market_making",
            variant_id="gate_block",
            features=["ob_imbalance"],
            parameters={},
            status="paper",
        )
    )
    _log_paper_metrics(agent, strategy_id, slippage=65.0)

    assessment = agent.evaluate_stage_gate(strategy_id, "live_canary")
    assert assessment["passed"] is False
    assert assessment["checks"]["slippage_mape"] is False


def test_research_cycle_returns_evidence_report(tmp_path):
    config = _agent_config(tmp_path)
    config["search_budget"] = 6
    config["top_performers"] = 2
    config["min_sharpe"] = -1.0
    config["min_deflated_sharpe"] = -2.0
    config["max_drawdown"] = 1.0
    agent = AIResearchAgent(config)

    report = agent.research_cycle(_historical_data(), strategy_types=["market_making"])

    assert report["summary"]["candidates_generated"] <= 6
    assert report["summary"]["backtests_run"] == report["summary"]["candidates_generated"]
    assert "objective" in report
    assert "profit_target_feasibility" in report["objective"]


def test_candidate_generation_round_robins_strategy_families(tmp_path):
    config = _agent_config(tmp_path)
    config["search_budget"] = 6
    agent = AIResearchAgent(config)

    candidates = agent._generate_candidates(
        [
            "market_making",
            "cross_sectional_momentum",
            "adaptive_trend",
        ],
        variants_per_type=10,
    )
    strategy_types = {candidate.strategy_type for candidate in candidates}

    assert len(candidates) == 6
    assert strategy_types == {
        "market_making",
        "cross_sectional_momentum",
        "adaptive_trend",
    }


def test_auto_generator_supports_swing_and_hold_variants():
    generator = AutoStrategyGenerator()

    swing = generator.generate_strategy_variants("swing_trend", n_per_feature_set=2)
    hold = generator.generate_strategy_variants("hold_carry", n_per_feature_set=2)
    xmom = generator.generate_strategy_variants("cross_sectional_momentum", n_per_feature_set=2)
    trend = generator.generate_strategy_variants("adaptive_trend", n_per_feature_set=2)
    reversion = generator.generate_strategy_variants("drawdown_reversion", n_per_feature_set=2)
    markov = generator.generate_strategy_variants("markov_regime", n_per_feature_set=2)

    assert swing
    assert hold
    assert xmom
    assert trend
    assert reversion
    assert markov
    assert all(variant.strategy_type == "swing_trend" for variant in swing)
    assert all(variant.strategy_type == "hold_carry" for variant in hold)
    assert all(variant.strategy_type == "cross_sectional_momentum" for variant in xmom)
    assert all(variant.strategy_type == "adaptive_trend" for variant in trend)
    assert all(variant.strategy_type == "drawdown_reversion" for variant in reversion)
    assert all(variant.strategy_type == "markov_regime" for variant in markov)


def test_stage_gate_uses_horizon_specific_thresholds(tmp_path):
    config = _agent_config(tmp_path)
    config["horizon_stage_gates"] = {
        "live_canary": {
            "swing": {
                "min_days": 20,
                "min_avg_sharpe": 0.8,
                "max_avg_drawdown": 0.2,
                "max_slippage_mape": 30.0,
                "max_kill_switch_triggers": 0,
            },
            "intraday": {
                "min_days": 30,
                "min_avg_sharpe": 1.2,
                "max_avg_drawdown": 0.15,
                "max_slippage_mape": 20.0,
                "max_kill_switch_triggers": 0,
            },
        }
    }
    agent = AIResearchAgent(config)

    swing_id = "swing_gate_pass"
    intraday_id = "intraday_gate_block"
    agent.db.log_experiment(
        Experiment(
            experiment_id=swing_id,
            strategy_name="swing_trend",
            variant_id="s1",
            features=["price_momentum_1h"],
            parameters={},
            status="paper",
        )
    )
    agent.db.log_experiment(
        Experiment(
            experiment_id=intraday_id,
            strategy_name="market_making",
            variant_id="i1",
            features=["ob_imbalance"],
            parameters={},
            status="paper",
        )
    )

    now = datetime.now(timezone.utc)
    for offset in range(22):
        payload = {
            "pnl": 80.0,
            "sharpe": 0.9,
            "drawdown": 0.1,
            "slippage_mape": 22.0,
            "kill_switch_triggers": 0,
        }
        agent.record_stage_metrics(
            swing_id,
            "paper",
            payload,
            timestamp=now - timedelta(days=offset),
        )
        agent.record_stage_metrics(
            intraday_id,
            "paper",
            payload,
            timestamp=now - timedelta(days=offset),
        )

    swing_assessment = agent.evaluate_stage_gate(swing_id, "live_canary")
    intraday_assessment = agent.evaluate_stage_gate(intraday_id, "live_canary")

    assert swing_assessment["horizon"] == "swing"
    assert swing_assessment["passed"] is True
    assert intraday_assessment["horizon"] == "intraday"
    assert intraday_assessment["passed"] is False


def test_extract_strategy_type_recommendations_from_report():
    report = {
        "top_strategies": [
            {"id": "a", "type": "market_making"},
            {"id": "b", "type": "swing_trend"},
            {"id": "c", "type": "market_making"},
            {"id": "d", "type": "hold_carry"},
        ]
    }
    names = AIResearchAgent.extract_strategy_type_recommendations(report, max_types=3)
    assert names == ["market_making", "swing_trend", "hold_carry"]


def test_monitor_paper_trading_demotes_when_model_drift_alerts(tmp_path):
    config = _agent_config(tmp_path)
    config["drift_monitor"] = {
        "enabled": True,
        "recent_days": 7,
        "baseline_days": 90,
        "max_sharpe_drop": 0.20,
        "max_drawdown_increase": 0.05,
        "max_slippage_mape_increase": 10.0,
        "min_recent_samples": 3,
    }
    agent = AIResearchAgent(config)
    strategy_id = "drift_monitor_case"

    agent.db.log_experiment(
        Experiment(
            experiment_id=strategy_id,
            strategy_name="market_making",
            variant_id="drift",
            features=["ob_imbalance"],
            parameters={},
            status="paper",
        )
    )
    agent.paper_trading.append(strategy_id)

    now = datetime.now(timezone.utc)
    for day in range(10, 35):
        agent.record_stage_metrics(
            strategy_id,
            "paper",
            {
                "pnl": 40.0,
                "sharpe": 1.3,
                "drawdown": 0.06,
                "slippage_mape": 12.0,
                "kill_switch_triggers": 0,
            },
            timestamp=now - timedelta(days=day),
        )
    for day in range(0, 7):
        agent.record_stage_metrics(
            strategy_id,
            "paper",
            {
                "pnl": -25.0,
                "sharpe": 0.2,
                "drawdown": 0.24,
                "slippage_mape": 38.0,
                "kill_switch_triggers": 0,
            },
            timestamp=now - timedelta(days=day),
        )

    payload = agent.monitor_paper_trading()

    assert payload[strategy_id]["status"] == "demoted"
    assert payload[strategy_id]["drift_alert"] is True
    assert strategy_id not in agent.paper_trading
