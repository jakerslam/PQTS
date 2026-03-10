from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import check_native_hotpath


def test_check_native_hotpath_tool_passes_on_repo_defaults(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["check_native_hotpath.py"])
    assert check_native_hotpath.main() == 0


def test_check_native_hotpath_tool_rejects_missing_symbol(tmp_path: Path, monkeypatch) -> None:
    cargo = tmp_path / "Cargo.toml"
    cargo.write_text("[package]\\nname='x'\\nversion='0.1.0'\\n", encoding="utf-8")
    lib = tmp_path / "lib.rs"
    lib.write_text("fn version() {}\\n", encoding="utf-8")
    matrix = tmp_path / "release_matrix.json"
    matrix.write_text(
        json.dumps(
            {
                "artifacts": [
                    {"target": "manylinux_x86_64", "python_version": "cp311", "wheel_tag": "cp311-manylinux_x86_64"},
                    {"target": "manylinux_x86_64", "python_version": "cp312", "wheel_tag": "cp312-manylinux_x86_64"},
                    {"target": "macos_arm64", "python_version": "cp311", "wheel_tag": "cp311-macosx_11_0_arm64"},
                    {"target": "macos_arm64", "python_version": "cp312", "wheel_tag": "cp312-macosx_11_0_arm64"},
                    {"target": "windows_amd64", "python_version": "cp311", "wheel_tag": "cp311-win_amd64"},
                    {"target": "windows_amd64", "python_version": "cp312", "wheel_tag": "cp312-win_amd64"},
                ]
            }
        ),
        encoding="utf-8",
    )
    policy = tmp_path / "migration_policy.json"
    policy.write_text(
        json.dumps(
            {
                "priority_modules": [
                    "orderbook_sequence",
                    "event_replay",
                    "risk_aware_router",
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "check_native_hotpath.py",
            "--cargo",
            str(cargo),
            "--lib",
            str(lib),
            "--matrix",
            str(matrix),
            "--policy",
            str(policy),
        ],
    )
    with pytest.raises(SystemExit, match="missing required symbols"):
        check_native_hotpath.main()
