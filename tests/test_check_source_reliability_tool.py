from __future__ import annotations

from pathlib import Path

from tools import check_source_reliability


def test_source_reliability_tool_passes_defaults(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["check_source_reliability.py"])
    assert check_source_reliability.main() == 0


def test_source_reliability_tool_fails_unclassified_claim(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "claims.md"
    target.write_text(
        "This source says Sharpe is 3.0 and profit doubled: https://example.com\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "check_source_reliability.py",
            "--target",
            str(target),
        ],
    )
    assert check_source_reliability.main() == 2
