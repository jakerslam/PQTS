from __future__ import annotations

import json
from pathlib import Path

from tools.check_full_srs_closure import evaluate


def test_full_srs_closure_passes_repo_artifacts() -> None:
    errors = evaluate(
        defaults_path=Path("config/strategy/assimilation_full_closure_defaults.json"),
        todo_path=Path("docs/TODO.md"),
        map_path=Path("docs/SRS_FULL_CLOSURE_EXECUTION_MAP.md"),
        srs_path=Path("docs/SRS.md"),
    )
    assert errors == []


def test_full_srs_closure_flags_unchecked_family(tmp_path: Path) -> None:
    defaults_path = tmp_path / "defaults.json"
    defaults_path.write_text(
        json.dumps(
            {
                "families": {
                    "AL": {
                        "refs": ["AL-1"],
                        "controls": {"policy_hook": "srs_baseline.al"},
                        "acceptance_evidence": ["ok"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    todo_path = tmp_path / "TODO.md"
    todo_path.write_text(
        "\n".join(
            [
                "## 02l. Full SRS Assimilation Closure (2026-03-10)",
                "- [ ] Assimilate AL requirement family (`Ref: AL-1`, `Evidence: x`)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    map_path = tmp_path / "MAP.md"
    map_path.write_text("## AL Family\n", encoding="utf-8")
    srs_path = tmp_path / "SRS.md"
    srs_path.write_text("### AL-1 Sample Requirement\n", encoding="utf-8")

    errors = evaluate(
        defaults_path=defaults_path,
        todo_path=todo_path,
        map_path=map_path,
        srs_path=srs_path,
    )
    assert any("not checked" in error for error in errors)
