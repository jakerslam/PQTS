from __future__ import annotations

import pytest

from tools import check_studio_contract


def test_check_studio_contract_tool_passes_defaults(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["check_studio_contract.py"])
    assert check_studio_contract.main() == 0


def test_check_studio_contract_tool_fails_for_missing_quickstart_command(tmp_path, monkeypatch) -> None:
    quickstart = tmp_path / "quickstart.md"
    quickstart.write_text("pqts init\n", encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "check_studio_contract.py",
            "--quickstart",
            str(quickstart),
        ],
    )
    with pytest.raises(SystemExit, match="quickstart missing command"):
        check_studio_contract.main()
