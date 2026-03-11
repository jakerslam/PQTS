from __future__ import annotations

import json
from pathlib import Path

from tools.audit_todo_dod import audit_todo


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_audit_unchecks_missing_evidence_and_adds_impact(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    coverage = tmp_path / "coverage.json"

    _write(
        todo,
        "\n".join(
            [
                "- [x] Item (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: ABC-1`)",
                "- [x] Item (`ROI: very_high`, `Type: engineering`, `Track: moat`, `Ref: ABC-2`, `Evidence: ok`)",
                "",
            ]
        ),
    )
    coverage.write_text(
        json.dumps(
            {
                "rows": [
                    {"id": "ABC-1", "status": "implemented"},
                    {"id": "ABC-2", "status": "implemented"},
                ]
            }
        ),
        encoding="utf-8",
    )

    stats = audit_todo(todo, coverage)
    out = todo.read_text(encoding="utf-8")
    assert "- [ ] Item" in out  # first item unmarked for missing evidence
    assert "Impact: 8" in out
    assert "Impact: 10" in out
    assert stats["unmarked_due_missing_evidence"] == 1

