from __future__ import annotations

from pathlib import Path

from tools.check_release_examples import _check_file


def test_check_file_accepts_placeholder(tmp_path: Path) -> None:
    path = tmp_path / "README.md"
    path.write_text("- Create tag (for example `vX.Y.Z`).\n", encoding="utf-8")
    assert _check_file(path, "0.1.5") == []


def test_check_file_flags_stale_tag(tmp_path: Path) -> None:
    path = tmp_path / "README.md"
    path.write_text("- Create tag (for example `v0.1.1`).\n", encoding="utf-8")
    errors = _check_file(path, "0.1.5")
    assert errors
    assert "stale release example tag v0.1.1" in errors[0]
