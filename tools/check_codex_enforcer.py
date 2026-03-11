#!/usr/bin/env python3
"""Validate codex enforcement docs and TODO evidence discipline."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REQ_HEADING_RE = re.compile(r"^###\s+((?:GIPP|MARIK|DUNIK|ZERQ|ANTP|MTM)-\d+)\b")
TODO_REF_RE = re.compile(r"Ref:\s*([^`]+)")
REQ_ID_RE = re.compile(r"\b(?:GIPP|MARIK|DUNIK|ZERQ|ANTP|MTM)-\d+\b")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_new_req_ids(srs_text: str) -> set[str]:
    out: set[str] = set()
    for line in srs_text.splitlines():
        match = REQ_HEADING_RE.match(line.strip())
        if match:
            out.add(match.group(1))
    return out


def _extract_todo_refs(todo_text: str) -> set[str]:
    out: set[str] = set()
    for line in todo_text.splitlines():
        ref_match = TODO_REF_RE.search(line)
        if not ref_match:
            continue
        out.update(REQ_ID_RE.findall(ref_match.group(1)))
    return out


def _checked_item_missing_required_fields(line: str) -> tuple[bool, bool]:
    token = line.strip()
    if not (token.startswith("- [x]") or token.startswith("- [X]")):
        return False, False
    ref_match = TODO_REF_RE.search(token)
    if not ref_match:
        return False, False
    if not REQ_ID_RE.search(ref_match.group(1)):
        return False, False
    return "Evidence:" not in token, "Impact:" not in token


def evaluate_codex_enforcer(
    *,
    agents_path: Path,
    compliance_path: Path,
    enforcer_path: Path,
    dod_path: Path,
    todo_path: Path,
    srs_path: Path,
) -> list[str]:
    errors: list[str] = []

    required_files = [agents_path, compliance_path, enforcer_path, dod_path, todo_path, srs_path]
    for path in required_files:
        if not path.exists():
            errors.append(f"missing required file: {path}")
    if errors:
        return errors

    agents = _read(agents_path)
    compliance = _read(compliance_path)
    enforcer = _read(enforcer_path)
    dod = _read(dod_path)
    todo = _read(todo_path)
    srs = _read(srs_path)

    if "docs/DEFINITION_OF_DONE.md" not in enforcer:
        errors.append("docs/CODEX_ENFORCER.md must reference docs/DEFINITION_OF_DONE.md")
    if "Required Completion Criteria" not in dod:
        errors.append("docs/DEFINITION_OF_DONE.md missing Required Completion Criteria section")
    if "docs/CODEX_ENFORCER.md" not in compliance:
        errors.append("docs/CODEX_COMPLIANCE.md must include docs/CODEX_ENFORCER.md in required references")
    if "docs/DEFINITION_OF_DONE.md" not in compliance:
        errors.append("docs/CODEX_COMPLIANCE.md must include docs/DEFINITION_OF_DONE.md in required references")
    if "docs/CODEX_ENFORCER.md" not in agents or "docs/DEFINITION_OF_DONE.md" not in agents:
        errors.append("AGENTS.md must include codex enforcement references to enforcer + DoD docs")

    if "SRS 66-71 Assimilation Execution Sprint" not in todo:
        errors.append("docs/TODO.md missing SRS 66-71 assimilation execution sprint section")

    for idx, line in enumerate(todo.splitlines(), start=1):
        missing_evidence, missing_impact = _checked_item_missing_required_fields(line)
        if missing_evidence:
            errors.append(f"docs/TODO.md:{idx} checked SRS 66-71 item missing Evidence field")
        if missing_impact:
            errors.append(f"docs/TODO.md:{idx} checked SRS 66-71 item missing Impact field")

    srs_ids = _extract_new_req_ids(srs)
    todo_ids = _extract_todo_refs(todo)
    missing_refs = sorted(srs_ids - todo_ids)
    if missing_refs:
        errors.append(f"docs/TODO.md missing references for SRS IDs: {', '.join(missing_refs)}")

    return errors


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agents", default="AGENTS.md")
    parser.add_argument("--compliance", default="docs/CODEX_COMPLIANCE.md")
    parser.add_argument("--enforcer", default="docs/CODEX_ENFORCER.md")
    parser.add_argument("--dod", default="docs/DEFINITION_OF_DONE.md")
    parser.add_argument("--todo", default="docs/TODO.md")
    parser.add_argument("--srs", default="docs/SRS.md")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    errors = evaluate_codex_enforcer(
        agents_path=Path(args.agents),
        compliance_path=Path(args.compliance),
        enforcer_path=Path(args.enforcer),
        dod_path=Path(args.dod),
        todo_path=Path(args.todo),
        srs_path=Path(args.srs),
    )
    payload = {"ok": not errors, "error_count": len(errors), "errors": errors}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
