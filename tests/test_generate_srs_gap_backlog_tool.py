from __future__ import annotations

from pathlib import Path

from tools import generate_srs_gap_backlog


def test_generate_srs_gap_backlog_tool_writes_markdown(tmp_path: Path, monkeypatch) -> None:
    srs = tmp_path / "SRS.md"
    srs.write_text(
        """
### FR-1 Example Requirement
- text

### PMKT-1 Example Adapter Requirement
- text
""".strip()
        + "\n",
        encoding="utf-8",
    )
    todo = tmp_path / "TODO.md"
    todo.write_text(
        """
- [x] done item (`Ref: PMKT-1`)
""".strip()
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "SRS_GAP_BACKLOG.md"

    monkeypatch.setattr(
        "sys.argv",
        [
            "generate_srs_gap_backlog.py",
            "--srs",
            str(srs),
            "--todo",
            str(todo),
            "--out",
            str(out),
        ],
    )
    assert generate_srs_gap_backlog.main() == 0
    text = out.read_text(encoding="utf-8")
    assert "FR-1" in text
    assert "PMKT-1" not in text
