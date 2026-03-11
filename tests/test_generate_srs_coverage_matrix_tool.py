from __future__ import annotations

from pathlib import Path

from tools.generate_srs_coverage_matrix import parse_todo_status


def test_parse_todo_status_ignores_human_only_rows(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    todo.write_text(
        "\n".join(
            [
                "- [ ] Human task (`Type: human_only`, `Ref: HUM-1`)",
                "- [x] Engineering done (`Type: engineering`, `Ref: ENG-1`)",
                "- [ ] Engineering open (`Type: engineering`, `Ref: ENG-2`)",
                "",
            ]
        ),
        encoding="utf-8",
    )

    status = parse_todo_status(todo)
    assert "HUM-1" not in status
    assert status["ENG-1"].state == "done"
    assert status["ENG-2"].state == "open"
