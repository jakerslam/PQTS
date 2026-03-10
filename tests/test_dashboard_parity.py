"""Tests for Streamlit↔Next dashboard parity checks."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analytics.dashboard_parity import compare_dashboard_metrics


def test_compare_dashboard_metrics_passes_when_within_tolerance() -> None:
    report = compare_dashboard_metrics(
        streamlit_metrics={"equity": 100000.0, "drawdown": 0.05},
        web_metrics={"equity": 100000.0001, "drawdown": 0.050001},
        metric_keys=["equity", "drawdown"],
        default_tolerance=0.01,
    )
    assert report.passed is True
    assert report.mismatches == 0


def test_compare_dashboard_metrics_flags_mismatches() -> None:
    report = compare_dashboard_metrics(
        streamlit_metrics={"equity": 100000.0, "drawdown": 0.05},
        web_metrics={"equity": 98000.0, "drawdown": 0.08},
        metric_keys=["equity", "drawdown"],
        default_tolerance=0.001,
    )
    assert report.passed is False
    assert report.mismatches == 2


def test_compare_dashboard_metrics_supports_tolerance_overrides() -> None:
    report = compare_dashboard_metrics(
        streamlit_metrics={"equity": 100000.0, "drawdown": 0.05},
        web_metrics={"equity": 99500.0, "drawdown": 0.05001},
        metric_keys=["equity", "drawdown"],
        default_tolerance=0.001,
        tolerance_overrides={"equity": 1000.0},
    )
    assert report.passed is True
    assert report.mismatches == 0
