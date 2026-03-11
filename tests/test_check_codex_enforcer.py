from __future__ import annotations

from pathlib import Path

from tools.check_codex_enforcer import evaluate_codex_enforcer


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_codex_enforcer_passes_repo_defaults() -> None:
    errors = evaluate_codex_enforcer(
        agents_path=Path("AGENTS.md"),
        compliance_path=Path("docs/CODEX_COMPLIANCE.md"),
        enforcer_path=Path("docs/CODEX_ENFORCER.md"),
        dod_path=Path("docs/DEFINITION_OF_DONE.md"),
        todo_path=Path("docs/TODO.md"),
        srs_path=Path("docs/SRS.md"),
    )
    assert errors == []


def test_codex_enforcer_flags_missing_evidence(tmp_path: Path) -> None:
    agents = tmp_path / "AGENTS.md"
    compliance = tmp_path / "docs/CODEX_COMPLIANCE.md"
    enforcer = tmp_path / "docs/CODEX_ENFORCER.md"
    dod = tmp_path / "docs/DEFINITION_OF_DONE.md"
    todo = tmp_path / "docs/TODO.md"
    srs = tmp_path / "docs/SRS.md"

    _write(
        agents,
        "# Agent\nrefs docs/CODEX_ENFORCER.md and docs/DEFINITION_OF_DONE.md\n",
    )
    _write(
        compliance,
        "docs/CODEX_ENFORCER.md\ndocs/DEFINITION_OF_DONE.md\n",
    )
    _write(
        enforcer,
        "read docs/DEFINITION_OF_DONE.md\n",
    )
    _write(
        dod,
        "## Required Completion Criteria\n",
    )
    _write(
        srs,
        "### GIPP-1 test\n### MARIK-1 test\n",
    )
    _write(
        todo,
        "\n".join(
            [
                "## SRS 66-71 Assimilation Execution Sprint",
                "- [x] Item (`Ref: GIPP-1`)",
                "- [ ] Item (`Ref: MARIK-1`)",
                "",
            ]
        ),
    )

    errors = evaluate_codex_enforcer(
        agents_path=agents,
        compliance_path=compliance,
        enforcer_path=enforcer,
        dod_path=dod,
        todo_path=todo,
        srs_path=srs,
    )
    assert any("missing Evidence field" in err for err in errors)


def test_codex_enforcer_flags_missing_impact(tmp_path: Path) -> None:
    agents = tmp_path / "AGENTS.md"
    compliance = tmp_path / "docs/CODEX_COMPLIANCE.md"
    enforcer = tmp_path / "docs/CODEX_ENFORCER.md"
    dod = tmp_path / "docs/DEFINITION_OF_DONE.md"
    todo = tmp_path / "docs/TODO.md"
    srs = tmp_path / "docs/SRS.md"

    _write(
        agents,
        "# Agent\nrefs docs/CODEX_ENFORCER.md and docs/DEFINITION_OF_DONE.md\n",
    )
    _write(
        compliance,
        "docs/CODEX_ENFORCER.md\ndocs/DEFINITION_OF_DONE.md\n",
    )
    _write(
        enforcer,
        "read docs/DEFINITION_OF_DONE.md\n",
    )
    _write(
        dod,
        "## Required Completion Criteria\n",
    )
    _write(
        srs,
        "### GIPP-1 test\n",
    )
    _write(
        todo,
        "\n".join(
            [
                "## SRS 66-71 Assimilation Execution Sprint",
                "- [x] Item (`Ref: GIPP-1`, `Evidence: ok`)",
                "",
            ]
        ),
    )

    errors = evaluate_codex_enforcer(
        agents_path=agents,
        compliance_path=compliance,
        enforcer_path=enforcer,
        dod_path=dod,
        todo_path=todo,
        srs_path=srs,
    )
    assert any("missing Impact field" in err for err in errors)
