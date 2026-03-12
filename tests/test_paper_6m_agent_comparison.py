"""Tests for the six-month agent vs standard harness comparison wrapper."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
MODULE_PATH = ROOT / "scripts" / "run_paper_6m_agent_comparison.py"
SPEC = importlib.util.spec_from_file_location("paper_6m_agent_comparison", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_compare_aggregates_computes_fill_rate_and_winner() -> None:
    comparison = MODULE.compare_aggregates(
        standard={
            "total_submitted": 100,
            "total_filled": 70,
            "avg_reject_rate": 0.30,
            "ready_months": 2,
            "passed": True,
        },
        agent={
            "total_submitted": 110,
            "total_filled": 88,
            "avg_reject_rate": 0.20,
            "ready_months": 3,
            "passed": True,
        },
    )
    assert comparison["standard"]["fill_rate"] == 0.7
    assert comparison["agent"]["fill_rate"] == 0.8
    assert comparison["delta"]["filled_delta"] == 18
    assert abs(comparison["delta"]["avg_reject_rate_delta"] - (-0.1)) < 1e-9
    assert comparison["winner_by_fill_rate"] == "agent"


def test_build_cmd_for_agent_applies_agent_specific_overrides() -> None:
    args = MODULE.build_parser().parse_args(
        [
            "--months",
            "6",
            "--risk-profile",
            "balanced",
            "--agent-risk-profile",
            "professional",
            "--agent-operator-tier",
            "pro",
            "--agent-max-reject-rate",
            "0.6",
            "--agent-max-avg-reject-rate",
            "0.35",
            "--agent-min-ready-months",
            "3",
        ]
    )
    cmd = MODULE._build_cmd_for_arm(  # noqa: SLF001
        args,
        arm="agent",
        out_dir=Path("data/reports/paper_6m_compare/agent"),
        tca_root=Path("data/tca/paper_6m_compare/agent"),
    )
    rendered = " ".join(str(token) for token in cmd)
    assert "--risk-profile professional" in rendered
    assert "--operator-tier pro" in rendered
    assert "--max-reject-rate 0.6" in rendered
    assert "--max-avg-reject-rate 0.35" in rendered
    assert "--min-ready-months 3" in rendered
