"""Tests for external repository assimilation ledger generation."""

from __future__ import annotations

from pathlib import Path

from tools.generate_external_repo_ledger import classify_path, LedgerRow, write_csv


def test_classify_freqtrade_strategy_interface_is_p0():
    category, phase, priority, target, notes = classify_path("freqtrade/strategy/interface.py")

    assert category == "strategy_interface"
    assert phase == "P0"
    assert priority == "high"
    assert "strategy" in target
    assert "PQTS-native" in notes


def test_classify_freqtrade_backtesting_is_p0():
    category, phase, priority, target, _notes = classify_path("freqtrade/optimize/backtesting.py")

    assert category == "backtesting_validation"
    assert phase == "P0"
    assert priority == "high"
    assert "run_real_money_validation" in target


def test_write_csv_includes_review_columns(tmp_path: Path):
    row = LedgerRow(
        source_repo="freqtrade/freqtrade",
        source_commit="abc123",
        path="freqtrade/strategy/interface.py",
        category="strategy_interface",
        review_phase="P0",
        priority="high",
        review_status="unreviewed",
        assimilation_decision="pending",
        pqts_target="src/research",
        license_boundary="GPL-3.0 study-only",
        size_bytes=10,
        line_count=1,
        sha256="abc",
        notes="note",
    )
    path = tmp_path / "ledger.csv"

    write_csv(path, [row])

    text = path.read_text(encoding="utf-8")
    assert "review_status" in text
    assert "assimilation_decision" in text
    assert "freqtrade/strategy/interface.py" in text
