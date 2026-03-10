from __future__ import annotations

import pytest

from tools import check_tier_safety_policy


def test_check_tier_safety_policy_tool_passes_defaults(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["check_tier_safety_policy.py"])
    assert check_tier_safety_policy.main() == 0


def test_check_tier_safety_policy_tool_fails_when_policy_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["check_tier_safety_policy.py", "--policy", "config/entitlements/missing.json"],
    )
    with pytest.raises(SystemExit, match="missing tier policy"):
        check_tier_safety_policy.main()
