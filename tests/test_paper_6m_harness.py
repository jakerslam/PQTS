"""Tests for six-month paper harness helpers."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
MODULE_PATH = ROOT / "scripts" / "run_paper_6m_harness.py"
SPEC = importlib.util.spec_from_file_location("paper_6m_harness", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_build_month_windows_returns_contiguous_six_month_range() -> None:
    windows = MODULE.build_month_windows(anchor_date=date(2026, 3, 10), months=6)
    assert len(windows) == 6
    assert windows[0][0] == date(2025, 9, 10)
    assert windows[-1][1] == date(2026, 3, 10)
    for left, right in zip(windows, windows[1:]):
        assert left[1] == right[0]


def test_aggregate_computes_pass_state() -> None:
    aggregate = MODULE._aggregate(  # noqa: SLF001
        monthly=[
            {
                "submitted": 10,
                "filled": 8,
                "rejected": 2,
                "ready_for_canary": True,
                "promotion_decision": "allow",
            },
            {
                "submitted": 12,
                "filled": 10,
                "rejected": 2,
                "ready_for_canary": False,
                "promotion_decision": "hold",
            },
        ],
        max_avg_reject_rate=0.3,
        min_ready_months=1,
    )
    assert aggregate["total_submitted"] == 22
    assert aggregate["total_filled"] == 18
    assert aggregate["ready_months"] == 1
    assert aggregate["passed"] is True
