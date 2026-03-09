"""Tests for architecture boundary checker."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "tools" / "check_architecture_boundaries.py"
SPEC = importlib.util.spec_from_file_location("check_architecture_boundaries", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_collect_boundary_violations_detects_invalid_cross_layer_import(tmp_path):
    _write(tmp_path / "modules" / "bad.py", "import app.runtime\n")
    _write(tmp_path / "modules" / "__init__.py", "")
    _write(tmp_path / "app" / "runtime.py", "")
    _write(tmp_path / "app" / "__init__.py", "")
    _write(tmp_path / "contracts" / "__init__.py", "")
    _write(tmp_path / "adapters" / "__init__.py", "")

    violations = MODULE.collect_boundary_violations(tmp_path)
    assert any("forbidden import 'app.runtime'" in item for item in violations)


def test_collect_boundary_violations_allows_valid_layer_imports(tmp_path):
    _write(tmp_path / "modules" / "ok.py", "from contracts.runtime import RuntimeContext\n")
    _write(tmp_path / "modules" / "__init__.py", "")
    _write(tmp_path / "contracts" / "runtime.py", "")
    _write(tmp_path / "contracts" / "__init__.py", "")
    _write(tmp_path / "adapters" / "__init__.py", "")
    _write(tmp_path / "app" / "__init__.py", "")

    violations = MODULE.collect_boundary_violations(tmp_path)
    assert violations == []
