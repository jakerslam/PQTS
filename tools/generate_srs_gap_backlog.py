#!/usr/bin/env python3
"""Generate prioritized backlog for non-implemented SRS requirements."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

try:
    from tools.generate_srs_coverage_matrix import (
        TODOStatus,
        parse_requirements,
        parse_todo_status,
    )
except ModuleNotFoundError:  # pragma: no cover - fallback for direct script execution
    from generate_srs_coverage_matrix import (  # type: ignore
        TODOStatus,
        parse_requirements,
        parse_todo_status,
    )

PRIORITY = {
    "FR": "P0",
    "NFR": "P0",
    "AC": "P0",
    "BF": "P0",
    "RV": "P0",
    "COMP": "P1",
    "PMKT": "P1",
    "LANG": "P1",
    "MOAT": "P1",
    "XR": "P1",
    "ZQ": "P1",
}


def _priority(prefix: str) -> str:
    return PRIORITY.get(prefix, "P2")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--srs", default="docs/SRS.md")
    parser.add_argument("--todo", default="docs/TODO.md")
    parser.add_argument("--out", default="docs/SRS_GAP_BACKLOG.md")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    srs_path = Path(args.srs)
    todo_path = Path(args.todo)
    out_path = Path(args.out)

    requirements = parse_requirements(srs_path)
    todo_map = parse_todo_status(todo_path)
    buckets: dict[str, list[tuple[str, str, str, str]]] = defaultdict(list)
    for req in requirements:
        todo_state = todo_map.get(req.req_id, TODOStatus()).state
        status = (
            "partial"
            if todo_state == "partial"
            else ("planned" if todo_state == "open" else ("implemented" if todo_state == "done" else "unmapped"))
        )
        if status == "implemented":
            continue
        buckets[_priority(req.prefix)].append((req.req_id, req.title, status, req.prefix))

    lines: list[str] = []
    lines.append("# SRS Gap Backlog")
    lines.append("")
    lines.append("Auto-generated from SRS coverage. Non-implemented requirements are grouped by priority.")
    lines.append("")

    for priority in ("P0", "P1", "P2"):
        rows = sorted(buckets.get(priority, []), key=lambda row: row[0])
        lines.append(f"## {priority}")
        lines.append("")
        lines.append(f"Count: **{len(rows)}**")
        lines.append("")
        lines.append("| ID | Prefix | Status | Requirement |")
        lines.append("|---|---|---|---|")
        for req_id, title, status, prefix in rows:
            title_escaped = title.replace("|", "\\|")
            lines.append(f"| {req_id} | {prefix} | {status} | {title_escaped} |")
        lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
