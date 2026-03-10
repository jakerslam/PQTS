from __future__ import annotations

import pytest

from tools import check_core_professional_contract


def test_check_core_professional_contract_tool_passes_defaults(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["check_core_professional_contract.py"])
    assert check_core_professional_contract.main() == 0


def test_check_core_professional_contract_tool_rejects_missing_script(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "check_core_professional_contract.py",
            "--required-scripts",
            "scripts/does_not_exist.py",
        ],
    )
    with pytest.raises(SystemExit, match="missing required core scripts"):
        check_core_professional_contract.main()
