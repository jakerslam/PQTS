"""Loop mode behavior tests for TradingEngine."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.engine import TradingEngine


def _base_engine_config(loop_mode: str) -> dict:
    return {
        "mode": "paper_trading",
        "runtime": {
            "loop": {
                "mode": loop_mode,
                "tick_interval_seconds": 0.01,
                "poll_interval_seconds": 0.01,
                "idle_sleep_seconds": 0.01,
                "error_backoff_seconds": 0.01,
            },
            "state_path": "data/test_engine_loop_state.json",
        },
        "markets": {
            "crypto": {"enabled": True},
            "equities": {"enabled": True},
            "forex": {"enabled": True},
        },
        "strategies": {
            "mean_reversion": {"enabled": True, "markets": ["equities"]},
        },
        "risk": {
            "initial_capital": 100000.0,
            "max_portfolio_risk_pct": 2.0,
            "max_position_risk_pct": 1.0,
            "max_drawdown_pct": 10.0,
            "max_correlation": 0.7,
            "max_positions": 20,
            "max_leverage": 3.0,
        },
    }


def _build_engine(tmp_path: Path, loop_mode: str) -> TradingEngine:
    config = _base_engine_config(loop_mode)
    config["runtime"]["state_path"] = str(tmp_path / f"{loop_mode}_engine_state.json")
    config_path = tmp_path / f"{loop_mode}_loop.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return TradingEngine(str(config_path))


def test_event_driven_loop_runs_strategy_only_on_market_change(tmp_path):
    engine = _build_engine(tmp_path, "event_driven")
    counters = {"updates": 0, "strategies": 0, "risk": 0}
    changes = iter([False, True, False, False])

    async def fake_update_market_data():
        counters["updates"] += 1
        changed = next(changes, False)
        if counters["updates"] >= 4:
            engine.running = False
        return changed

    async def fake_run_strategies():
        counters["strategies"] += 1

    async def fake_check_risk_limits():
        counters["risk"] += 1

    engine._update_market_data = fake_update_market_data  # type: ignore[method-assign]
    engine._run_strategies = fake_run_strategies  # type: ignore[method-assign]
    engine._check_risk_limits = fake_check_risk_limits  # type: ignore[method-assign]
    engine.running = True

    asyncio.run(engine._main_loop())

    assert counters["updates"] == 4
    assert counters["strategies"] == 1
    assert counters["risk"] == 1


def test_tick_loop_runs_strategy_every_tick_even_without_market_change(tmp_path):
    engine = _build_engine(tmp_path, "tick")
    counters = {"updates": 0, "strategies": 0, "risk": 0}

    async def fake_update_market_data():
        counters["updates"] += 1
        if counters["updates"] >= 3:
            engine.running = False
        return False

    async def fake_run_strategies():
        counters["strategies"] += 1

    async def fake_check_risk_limits():
        counters["risk"] += 1

    engine._update_market_data = fake_update_market_data  # type: ignore[method-assign]
    engine._run_strategies = fake_run_strategies  # type: ignore[method-assign]
    engine._check_risk_limits = fake_check_risk_limits  # type: ignore[method-assign]
    engine.running = True

    asyncio.run(engine._main_loop())

    assert counters["updates"] == 3
    assert counters["strategies"] == 3
    assert counters["risk"] == 3


def test_engine_applies_low_latency_profile_defaults_when_loop_overrides_missing(tmp_path):
    config = _base_engine_config("event_driven")
    config["runtime"].pop("loop", None)
    config["runtime"]["performance"] = {"profile": "low_latency"}
    config["runtime"]["state_path"] = str(tmp_path / "perf_state.json")
    config_path = tmp_path / "perf_profile.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    engine = TradingEngine(str(config_path))

    assert engine.performance_profile == "low_latency"
    assert engine.loop_tick_interval_seconds == pytest.approx(0.05)
    assert engine.loop_poll_interval_seconds == pytest.approx(0.01)
    assert engine.loop_idle_sleep_seconds == pytest.approx(0.02)


def test_engine_rejects_required_native_hotpath_when_unavailable(tmp_path, monkeypatch):
    config = _base_engine_config("event_driven")
    config["runtime"]["performance"] = {
        "profile": "low_latency",
        "require_native_hotpath": True,
    }
    config["runtime"]["state_path"] = str(tmp_path / "native_required_state.json")
    config_path = tmp_path / "native_required.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    monkeypatch.setattr("core.engine.native_available", lambda: False)

    with pytest.raises(RuntimeError, match="require_native_hotpath"):
        TradingEngine(str(config_path))
