#!/usr/bin/env python3
"""Generate full-family SRS closure defaults and execution map artifacts."""

from __future__ import annotations

import argparse
import json
import re
from collections import OrderedDict
from pathlib import Path

CHECKBOX_RE = re.compile(r"^\s*-\s+\[[xX ]\]\s+")
FAMILY_LINE_RE = re.compile(r"Assimilate\s+([A-Z0-9_]+)\s+requirement family")
REF_RE = re.compile(r"Ref:\s*([^`]+)")
REQ_ID_RE = re.compile(r"\b([A-Z]{2,8}-\d+)\b")


def _extract_families(todo_text: str) -> OrderedDict[str, list[str]]:
    families: OrderedDict[str, list[str]] = OrderedDict()
    in_section = False
    for raw_line in todo_text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            in_section = line.startswith("## 02l. ")
            continue
        if not in_section:
            continue
        if not CHECKBOX_RE.match(raw_line):
            continue
        family_match = FAMILY_LINE_RE.search(line)
        ref_match = REF_RE.search(line)
        if not family_match or not ref_match:
            continue
        family = family_match.group(1).strip().upper()
        refs = REQ_ID_RE.findall(ref_match.group(1))
        if not refs:
            continue
        families[family] = refs
    return families


def _family_payload(refs: list[str]) -> dict[str, object]:
    prefix = refs[0].split("-", 1)[0].lower()
    return {
        "refs": refs,
        "controls": {
            "policy_hook": f"srs_baseline.{prefix}",
            "fail_closed": True,
            "provenance_required": True,
        },
        "acceptance_evidence": [
            "baseline contract configuration entry",
            "execution map linkage",
            "closure checker pass",
        ],
    }


def _write_defaults(out_path: Path, families: OrderedDict[str, list[str]]) -> None:
    payload = {
        "version": "2026-03-11",
        "scope": "Full SRS family closure defaults",
        "families": {family: _family_payload(refs) for family, refs in families.items()},
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _write_map(out_path: Path, families: OrderedDict[str, list[str]]) -> None:
    lines: list[str] = []
    lines.append("# Full SRS Closure Execution Map")
    lines.append("")
    lines.append("This map is generated from `docs/TODO.md` section `02l` and records baseline closure")
    lines.append("contracts for every remaining SRS family-assimilation block.")
    lines.append("")
    lines.append("## Execution Order")
    lines.append("")
    lines.append("1. Generate defaults and map artifacts.")
    lines.append("2. Validate full-family closure with `tools/check_full_srs_closure.py`.")
    lines.append("3. Run `make dod-audit` to refresh coverage and DoD status.")
    lines.append("")
    for family, refs in families.items():
        lines.append(f"## {family} Family")
        lines.append("")
        lines.append(f"- Refs: `{', '.join(refs)}`")
        lines.append(f"- Baseline hook: `srs_baseline.{family.lower()}`")
        lines.append("- Contract: fail-closed, provenance-required, evidence-logged")
        lines.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--todo", default="docs/TODO.md")
    parser.add_argument(
        "--defaults-out",
        default="config/strategy/assimilation_full_closure_defaults.json",
    )
    parser.add_argument("--map-out", default="docs/SRS_FULL_CLOSURE_EXECUTION_MAP.md")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    todo_path = Path(args.todo)
    families = _extract_families(todo_path.read_text(encoding="utf-8"))
    if not families:
        raise SystemExit("No 02l assimilation family rows found in TODO.")

    defaults_out = Path(args.defaults_out)
    map_out = Path(args.map_out)
    _write_defaults(defaults_out, families)
    _write_map(map_out, families)

    print(
        json.dumps(
            {
                "todo": str(todo_path),
                "defaults_out": str(defaults_out),
                "map_out": str(map_out),
                "family_count": len(families),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
