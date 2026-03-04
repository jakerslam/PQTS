"""CLI helper tests for scripts/run_paper_campaign.py."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "scripts" / "run_paper_campaign.py"
SPEC = importlib.util.spec_from_file_location("run_paper_campaign", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_parser_accepts_risk_profile_and_symbols():
    parser = MODULE.build_arg_parser()
    args = parser.parse_args(
        [
            "--risk-profile",
            "professional",
            "--symbols",
            "BTCUSDT,ETHUSDT",
            "--cycles",
            "12",
        ]
    )

    assert args.risk_profile == "professional"
    assert args.symbols == "BTCUSDT,ETHUSDT"
    assert args.cycles == 12


def test_snapshot_computes_revenue_before_promotion_gate():
    source = inspect.getsource(MODULE._run)
    revenue_idx = source.find("revenue_payload = revenue_diagnostics.payload")
    promotion_idx = source.find("promotion_gate = evaluate_promotion_gate")
    assert revenue_idx != -1
    assert promotion_idx != -1
    assert revenue_idx < promotion_idx
