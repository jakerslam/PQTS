#!/usr/bin/env python3
"""Audit TODO checklist items against DoD and normalize Impact metadata."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CHECK_RE = re.compile(r"^(\s*)- \[([xX ])\] (.*)$")
REF_RE = re.compile(r"Ref:\s*([^`]+)")
REQ_ID_RE = re.compile(r"\b([A-Z]{2,8}-\d+)\b")
ROI_RE = re.compile(r"ROI:\s*(very_high|high|medium|low)", re.IGNORECASE)
TRACK_RE = re.compile(r"Track:\s*(parity|moat)", re.IGNORECASE)
IMPACT_RE = re.compile(r"Impact:\s*(10|[1-9])")


def _load_coverage(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for row in payload.get("rows", []):
        req_id = row.get("id")
        status = row.get("status")
        if isinstance(req_id, str) and isinstance(status, str):
            out[req_id] = status
    return out


def _impact_for_line(text: str) -> int:
    roi = "high"
    track = "parity"
    roi_match = ROI_RE.search(text)
    track_match = TRACK_RE.search(text)
    if roi_match:
        roi = roi_match.group(1).lower()
    if track_match:
        track = track_match.group(1).lower()

    base = {
        "very_high": 10,
        "high": 8,
        "medium": 6,
        "low": 4,
    }.get(roi, 7)
    bonus = 1 if track == "moat" and base < 10 else 0
    return min(10, base + bonus)


def _extract_refs(text: str) -> list[str]:
    match = REF_RE.search(text)
    if not match:
        return []
    refs = REQ_ID_RE.findall(match.group(1))
    return refs


def _ensure_impact_metadata(text: str, impact: int) -> tuple[str, bool]:
    if IMPACT_RE.search(text):
        updated = IMPACT_RE.sub(f"Impact: {impact}", text, count=1)
        return updated, updated != text

    if text.rstrip().endswith(")"):
        idx = text.rfind(")")
        return f"{text[:idx]}, `Impact: {impact}`{text[idx:]}", True
    return f"{text} (`Impact: {impact}`)", True


def audit_todo(todo_path: Path, coverage_path: Path) -> dict[str, int]:
    lines = todo_path.read_text(encoding="utf-8").splitlines()
    coverage = _load_coverage(coverage_path)

    out_lines: list[str] = []
    checked_before = 0
    checked_after = 0
    unchecked_before = 0
    unchecked_after = 0
    unmarked_due_missing_evidence = 0
    unmarked_due_nonimplemented_ref = 0
    impact_added_or_updated = 0
    ref_items = 0

    for line in lines:
        match = CHECK_RE.match(line)
        if not match:
            out_lines.append(line)
            continue

        indent, mark, body = match.groups()
        checked = mark.lower() == "x"
        if checked:
            checked_before += 1
        else:
            unchecked_before += 1

        refs = _extract_refs(body)
        has_ref = bool(refs)
        if has_ref:
            ref_items += 1
            impact = _impact_for_line(body)
            body, changed = _ensure_impact_metadata(body, impact)
            if changed:
                impact_added_or_updated += 1

            has_evidence = "Evidence:" in body
            refs_implemented = all(coverage.get(req_id) == "implemented" for req_id in refs)

            # DoD enforcement: any checked item with refs must have Evidence and implemented refs.
            if checked and not has_evidence:
                checked = False
                unmarked_due_missing_evidence += 1
            elif checked and not refs_implemented:
                checked = False
                unmarked_due_nonimplemented_ref += 1

        prefix = f"{indent}- [{'x' if checked else ' '}] "
        out_line = f"{prefix}{body}"
        out_lines.append(out_line)

        if checked:
            checked_after += 1
        else:
            unchecked_after += 1

    todo_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return {
        "checked_before": checked_before,
        "checked_after": checked_after,
        "unchecked_before": unchecked_before,
        "unchecked_after": unchecked_after,
        "unmarked_due_missing_evidence": unmarked_due_missing_evidence,
        "unmarked_due_nonimplemented_ref": unmarked_due_nonimplemented_ref,
        "impact_added_or_updated": impact_added_or_updated,
        "ref_items": ref_items,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--todo", default="docs/TODO.md")
    parser.add_argument("--coverage", default="data/reports/srs_coverage/srs_coverage.json")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    stats = audit_todo(Path(args.todo), Path(args.coverage))
    print(json.dumps(stats, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

