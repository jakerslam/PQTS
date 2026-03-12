"""Tests for strategy studio preview and advanced training helpers."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from research.advanced_training import (  # noqa: E402
    run_adaptive_ensemble_training,
    run_evolutionary_search,
    run_rl_training,
)
from research.anti_leakage_validator import (  # noqa: E402
    summarize_leakage_report,
    validate_no_lookahead,
)
from research.strategy_studio import build_strategy_graph, simulate_preview  # noqa: E402


def test_validate_no_lookahead_detects_future_feature_timestamp() -> None:
    report = validate_no_lookahead(
        [
            {"feature_ts": "2026-03-10T00:00:00", "target_ts": "2026-03-10T00:00:01"},
            {"feature_ts": "2026-03-10T00:00:03", "target_ts": "2026-03-10T00:00:02"},
        ]
    )
    assert report["checked_rows"] == 2
    assert report["passed"] is False
    assert len(report["violations"]) == 1
    assert "FAIL" in summarize_leakage_report(report)


def test_strategy_studio_preview_returns_compile_and_leakage_report() -> None:
    graph = build_strategy_graph(
        {
            "strategy_id": "market_making",
            "nodes": [{"node_id": "n1", "kind": "signal", "params": {"window": 20}}],
            "edges": [["n1", "sink"]],
        }
    )
    preview = simulate_preview(
        strategy_id="market_making",
        graph=graph,
        code="def generate_signal(x):\n    return x\n",
        sample_rows=[{"feature_ts": "2026-03-10T00:00:00", "target_ts": "2026-03-10T00:00:00"}],
    )
    assert preview["compile_report"]["compiled"] is True
    assert preview["leakage_report"]["passed"] is True
    assert preview["preview_quality_score"] > 0.0


def test_training_artifacts_cover_adaptive_rl_and_evolutionary_modes() -> None:
    adaptive = run_adaptive_ensemble_training(
        strategy_id="trend_following",
        candidate_models=[{"score": 0.6}, {"score": 0.7}],
        retrain_on_live_data=True,
        optuna_trials=64,
    )
    rl = run_rl_training(strategy_id="trend_following", episodes=250, reward_mean=0.3, reward_std=0.2)
    evo = run_evolutionary_search(
        strategy_id="trend_following",
        generations=40,
        population_size=128,
        best_fitness=0.5,
    )
    assert adaptive.mode == "adaptive_ensemble"
    assert rl.mode == "rl"
    assert evo.mode == "evolutionary"
    assert adaptive.to_dict()["strategy_id"] == "trend_following"
    assert rl.to_dict()["score"] >= -1.0
    assert evo.to_dict()["score"] <= 1.0
