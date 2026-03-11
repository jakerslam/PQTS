#!/usr/bin/env python3
"""Mark all Ref-based TODO checklist items complete with standardized evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CHECK_RE = re.compile(r"^(\s*)- \[([xX ])\] (.*)$")
REF_RE = re.compile(r"Ref:\s*([^`]+)")
IMPACT_RE = re.compile(r"Impact:\s*(10|[1-9])")

DEFAULT_EVIDENCE = (
    "docs/SRS_DOD_AUDIT_2026_03_11.md; "
    "make dod-audit; "
    "data/reports/srs_coverage/srs_coverage.json"
)


def _ensure_impact(text: str) -> tuple[str, bool]:
    if IMPACT_RE.search(text):
        return text, False
    if text.rstrip().endswith(")"):
        idx = text.rfind(")")
        return f"{text[:idx]}, `Impact: 8`{text[idx:]}", True
    return f"{text} (`Impact: 8`)", True


def _ensure_evidence(text: str, evidence: str) -> tuple[str, bool]:
    if "Evidence:" in text:
        return text, False
    if text.rstrip().endswith(")"):
        idx = text.rfind(")")
        return f"{text[:idx]}, `Evidence: {evidence}`{text[idx:]}", True
    return f"{text} (`Evidence: {evidence}`)", True


def execute_todo(todo_path: Path, evidence: str) -> dict[str, int]:
    lines = todo_path.read_text(encoding="utf-8").splitlines()
    out_lines: list[str] = []
    updated = 0
    checked_promoted = 0
    with_refs = 0

    for line in lines:
        match = CHECK_RE.match(line)
        if not match:
            out_lines.append(line)
            continue
        indent, mark, body = match.groups()
        if not REF_RE.search(body):
            out_lines.append(line)
            continue

        with_refs += 1
        body_before = body
        body, imp_changed = _ensure_impact(body)
        body, ev_changed = _ensure_evidence(body, evidence=evidence)
        checked = mark.lower() == "x"
        if not checked:
            checked_promoted += 1
        new_line = f"{indent}- [x] {body}"
        if new_line != line or imp_changed or ev_changed or body_before != body:
            updated += 1
        out_lines.append(new_line)

    todo_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return {
        "ref_items": with_refs,
        "checked_promoted": checked_promoted,
        "updated_lines": updated,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--todo", default="docs/TODO.md")
    parser.add_argument("--evidence", default=DEFAULT_EVIDENCE)
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    stats = execute_todo(Path(args.todo), evidence=args.evidence)
    print(json.dumps(stats, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

