#!/usr/bin/env python3
"""Validate full-family SRS closure defaults, map, and TODO status."""

from __future__ import annotations

import argparse
import json
import re
from collections import OrderedDict
from pathlib import Path

CHECKBOX_RE = re.compile(r"^\s*-\s+\[([xX ])\]\s+")
FAMILY_LINE_RE = re.compile(r"Assimilate\s+([A-Z0-9_]+)\s+requirement family")
REF_RE = re.compile(r"Ref:\s*([^`]+)")
REQ_ID_RE = re.compile(r"\b([A-Z]{2,8}-\d+)\b")
SRS_HEADING_RE = re.compile(r"^###\s+([A-Z]{2,8}-\d+)\s+")


def _extract_todo_families(todo_text: str) -> OrderedDict[str, dict[str, object]]:
    families: OrderedDict[str, dict[str, object]] = OrderedDict()
    in_section = False
    for idx, raw_line in enumerate(todo_text.splitlines(), start=1):
        line = raw_line.strip()
        if line.startswith("## "):
            in_section = line.startswith("## 02l. ")
            continue
        if not in_section:
            continue
        check_match = CHECKBOX_RE.match(raw_line)
        if not check_match:
            continue
        family_match = FAMILY_LINE_RE.search(line)
        ref_match = REF_RE.search(line)
        if not family_match or not ref_match:
            continue
        family = family_match.group(1).upper()
        refs = REQ_ID_RE.findall(ref_match.group(1))
        families[family] = {
            "checked": check_match.group(1).lower() == "x",
            "refs": refs,
            "line_no": idx,
            "line": line,
        }
    return families


def _extract_srs_ids(srs_text: str) -> set[str]:
    ids: set[str] = set()
    for line in srs_text.splitlines():
        match = SRS_HEADING_RE.match(line.strip())
        if not match:
            continue
        ids.add(match.group(1))
    return ids


def evaluate(
    *,
    defaults_path: Path,
    todo_path: Path,
    map_path: Path,
    srs_path: Path,
) -> list[str]:
    errors: list[str] = []
    for path in (defaults_path, todo_path, map_path, srs_path):
        if not path.exists():
            errors.append(f"missing file: {path}")
    if errors:
        return errors

    defaults = json.loads(defaults_path.read_text(encoding="utf-8"))
    families = defaults.get("families")
    if not isinstance(families, dict):
        return [f"{defaults_path} missing 'families' object"]

    todo_families = _extract_todo_families(todo_path.read_text(encoding="utf-8"))
    if not todo_families:
        return ["no 02l family-assimilation rows found in TODO"]

    srs_ids = _extract_srs_ids(srs_path.read_text(encoding="utf-8"))
    map_text = map_path.read_text(encoding="utf-8")

    for family, todo_meta in todo_families.items():
        block = families.get(family)
        if not isinstance(block, dict):
            errors.append(f"missing defaults family block: {family}")
            continue
        refs = block.get("refs")
        if refs != todo_meta["refs"]:
            errors.append(
                f"{family} refs mismatch between defaults and TODO line {todo_meta['line_no']}: "
                f"{refs} vs {todo_meta['refs']}"
            )
        if not todo_meta["checked"]:
            errors.append(f"TODO family row not checked: {family} (line {todo_meta['line_no']})")
        if "Evidence:" not in str(todo_meta["line"]):
            errors.append(f"TODO family row missing Evidence: {family} (line {todo_meta['line_no']})")
        if not isinstance(block.get("controls"), dict) or not block.get("controls"):
            errors.append(f"{family} controls missing/empty")
        if not isinstance(block.get("acceptance_evidence"), list) or not block.get("acceptance_evidence"):
            errors.append(f"{family} acceptance_evidence missing/empty")
        for req_id in todo_meta["refs"]:
            if req_id not in srs_ids:
                errors.append(f"{family} references missing SRS requirement: {req_id}")
        if f"## {family} Family" not in map_text:
            errors.append(f"execution map missing section: {family}")

    extra_defaults = sorted(set(families.keys()) - set(todo_families.keys()))
    if extra_defaults:
        errors.append(f"defaults contain families not present in TODO 02l: {', '.join(extra_defaults)}")

    return errors


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--defaults", default="config/strategy/assimilation_full_closure_defaults.json")
    parser.add_argument("--todo", default="docs/TODO.md")
    parser.add_argument("--map", default="docs/SRS_FULL_CLOSURE_EXECUTION_MAP.md")
    parser.add_argument("--srs", default="docs/SRS.md")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    errors = evaluate(
        defaults_path=Path(args.defaults),
        todo_path=Path(args.todo),
        map_path=Path(args.map),
        srs_path=Path(args.srs),
    )
    payload = {"ok": not errors, "error_count": len(errors), "errors": errors}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
