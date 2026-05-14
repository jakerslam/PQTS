"""CLI helper tests for scripts/run_real_money_validation.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "scripts" / "run_real_money_validation.py"
SPEC = importlib.util.spec_from_file_location("run_real_money_validation", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_parser_defaults_keep_live_money_gated():
    parser = MODULE.build_parser()
    args = parser.parse_args(["--start", "2026-01-01", "--end", "2026-02-01"])

    assert args.run_paper_smoke is False
    assert args.paper_min_days == 30
    assert args.paper_min_fills == 200
    assert "cross_sectional_momentum" in args.strategy_types
    assert "adaptive_trend" in args.strategy_types
    assert "drawdown_reversion" in args.strategy_types
    assert "markov_regime" in args.strategy_types


def test_prepare_agent_config_isolates_research_outputs(tmp_path: Path):
    parser = MODULE.build_parser()
    args = parser.parse_args(["--start", "2026-01-01", "--end", "2026-02-01"])
    run_dir = tmp_path / "validation"

    config = MODULE._prepare_agent_config(
        base_config={"analytics": {"report_schema_version": "1.0.0"}, "search_budget": 100},
        run_dir=run_dir,
        args=args,
    )

    assert config["db_path"] == str(run_dir / "research.db")
    assert config["analytics"]["report_dir"] == str(run_dir / "research_reports")
    assert config["analytics"]["artifact_registry_dir"] == str(run_dir / "research_artifacts")
    assert config["search_budget"] == args.search_budget
    assert config["walk_forward"]["train_years"] == args.wf_train_years


def test_payload_promotable_requires_all_gates_and_positive_alpha():
    payload = {
        "purged_cv_passed": True,
        "walk_forward_passed": True,
        "deflated_sharpe_passed": True,
        "parameter_stability_passed": True,
        "regime_robustness_passed": True,
        "expected_alpha_bps": 4.2,
    }

    assert MODULE._payload_is_promotable(payload) is True
    payload["expected_alpha_bps"] = 0.0
    assert MODULE._payload_is_promotable(payload) is False
    payload["expected_alpha_bps"] = 4.2
    payload["deflated_sharpe_passed"] = False
    assert MODULE._payload_is_promotable(payload) is False


def test_paper_command_uses_research_validation_and_no_alpha_override(tmp_path: Path):
    parser = MODULE.build_parser()
    args = parser.parse_args(
        [
            "--start",
            "2026-01-01",
            "--end",
            "2026-02-01",
            "--run-paper-smoke",
        ]
    )
    command = MODULE._build_paper_command(
        args=args,
        run_dir=tmp_path,
        research_validation_path=tmp_path / "payload.json",
    )
    joined = " ".join(command)

    assert "run_paper_campaign.py" in joined
    assert "--research-validation" in command
    assert "--require-research-alpha" in command
    assert "--campaign-expected-alpha-bps" not in command
