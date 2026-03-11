from __future__ import annotations

from pathlib import Path

from tools.audit_todo_code_only import audit_todo_code_only


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_code_only_audit_unchecks_missing_code_and_test(tmp_path: Path) -> None:
    todo = tmp_path / "docs/TODO.md"
    _write(tmp_path / "src/module.py", "def f():\n    return 1\n")
    _write(
        todo,
        "\n".join(
            [
                "- [x] Docs-only (`Type: engineering`, `Ref: ABC-1`, `Evidence: docs/a.md; make dod-audit`)",
                "- [x] Code-no-test (`Type: engineering`, `Ref: ABC-2`, `Evidence: src/module.py`)",
                "- [x] Fully-backed (`Type: engineering`, `Ref: ABC-3`, `Evidence: src/module.py; make test`)",
                "",
            ]
        ),
    )

    stats = audit_todo_code_only(todo, repo_root=tmp_path)
    out = todo.read_text(encoding="utf-8")
    lines = [line for line in out.splitlines() if line.startswith("- [")]

    assert lines[0].startswith("- [ ]")
    assert lines[1].startswith("- [ ]")
    assert lines[2].startswith("- [x]")
    assert stats["unmarked_missing_code_evidence"] == 1
    assert stats["unmarked_missing_test_evidence"] == 1


def test_code_only_audit_excludes_human_only_items(tmp_path: Path) -> None:
    todo = tmp_path / "docs/TODO.md"
    _write(
        todo,
        "\n".join(
            [
                "- [x] Human item (`Type: human_only`, `Ref: HUM-1`, `Evidence: docs/human.md`)",
                "",
            ]
        ),
    )

    stats = audit_todo_code_only(todo, repo_root=tmp_path)
    out = todo.read_text(encoding="utf-8")
    assert "- [x] Human item" in out
    assert stats["excluded_human_only_ref_items"] == 1
