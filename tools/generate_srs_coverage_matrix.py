#!/usr/bin/env python3
"""Generate SRS coverage artifacts from docs/SRS.md, docs/TODO.md, and repo evidence."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ID_RE = re.compile(r"\b([A-Z]{2,6}-\d+)\b")
HEADING_RE = re.compile(r"^###\s+([A-Z]{2,6}-\d+)\s+(.+?)\s*$")
REF_RE = re.compile(r"Ref:\s*([^`]+)")


@dataclass(frozen=True)
class Requirement:
    req_id: str
    title: str
    prefix: str


@dataclass
class TODOStatus:
    done: bool = False
    open: bool = False

    @property
    def state(self) -> str:
        if self.done and self.open:
            return "partial"
        if self.done:
            return "done"
        if self.open:
            return "open"
        return "none"


def parse_requirements(srs_path: Path) -> list[Requirement]:
    requirements: list[Requirement] = []
    for line in srs_path.read_text(encoding="utf-8").splitlines():
        match = HEADING_RE.match(line.strip())
        if not match:
            continue
        req_id = match.group(1)
        title = match.group(2).strip()
        prefix = req_id.split("-", 1)[0]
        requirements.append(Requirement(req_id=req_id, title=title, prefix=prefix))
    seen: set[str] = set()
    deduped: list[Requirement] = []
    for item in requirements:
        if item.req_id in seen:
            continue
        seen.add(item.req_id)
        deduped.append(item)
    return deduped


def parse_todo_status(todo_path: Path) -> dict[str, TODOStatus]:
    out: dict[str, TODOStatus] = defaultdict(TODOStatus)
    for line in todo_path.read_text(encoding="utf-8").splitlines():
        token = line.strip()
        if not token.startswith("- ["):
            continue
        # Human-only tasks do not represent automatable engineering coverage.
        if "Type: human_only" in token:
            continue
        checked = token.startswith("- [x]") or token.startswith("- [X]")
        ref_match = REF_RE.search(token)
        if not ref_match:
            continue
        refs = [item.strip().strip("`") for item in ref_match.group(1).split(",") if item.strip()]
        for req_id in refs:
            if not ID_RE.fullmatch(req_id):
                continue
            status = out[req_id]
            if checked:
                status.done = True
            else:
                status.open = True
    return out


def iter_text_files(root: Path) -> Iterable[Path]:
    skip_dirs = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
    }
    skip_suffixes = {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".pdf",
        ".csv",
        ".parquet",
        ".zip",
        ".gz",
        ".ico",
        ".woff",
        ".woff2",
    }
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        parts = set(rel.parts)
        if parts.intersection(skip_dirs):
            continue
        if path.suffix.lower() in skip_suffixes:
            continue
        yield path


def build_evidence_index(root: Path, excluded: set[Path]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = defaultdict(set)
    for path in iter_text_files(root):
        if path in excluded:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        matches = set(ID_RE.findall(text))
        if not matches:
            continue
        rel = str(path.relative_to(root))
        for req_id in matches:
            index[req_id].add(rel)
    return index


def classify(todo_state: str, evidence_files: list[str]) -> str:
    if todo_state == "done":
        return "implemented"
    if todo_state == "partial":
        return "partial"
    if todo_state == "open":
        return "planned"
    if evidence_files:
        return "traced"
    return "unmapped"


def write_markdown(
    *,
    out_path: Path,
    rows: list[dict[str, object]],
    status_counts: Counter[str],
    prefix_counts: dict[str, Counter[str]],
) -> None:
    lines: list[str] = []
    lines.append("# SRS Coverage Matrix")
    lines.append("")
    lines.append("This matrix is auto-generated from `docs/SRS.md`, `docs/TODO.md`, and repository evidence scans.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total requirements: **{len(rows)}**")
    for key in ("implemented", "partial", "planned", "traced", "unmapped"):
        lines.append(f"- {key}: **{status_counts.get(key, 0)}**")
    lines.append("")
    lines.append("## Prefix Summary")
    lines.append("")
    lines.append("| Prefix | Implemented | Partial | Planned | Traced | Unmapped | Total |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for prefix in sorted(prefix_counts):
        counts = prefix_counts[prefix]
        total = sum(counts.values())
        lines.append(
            "| "
            + " | ".join(
                [
                    prefix,
                    str(counts.get("implemented", 0)),
                    str(counts.get("partial", 0)),
                    str(counts.get("planned", 0)),
                    str(counts.get("traced", 0)),
                    str(counts.get("unmapped", 0)),
                    str(total),
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("## Requirement Matrix")
    lines.append("")
    lines.append("| ID | Title | Status | TODO | Evidence |")
    lines.append("|---|---|---|---|---|")
    for row in rows:
        evidence = row["evidence_files"]
        evidence_str = ", ".join(evidence[:3]) if evidence else "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["id"]),
                    str(row["title"]).replace("|", "\\|"),
                    str(row["status"]),
                    str(row["todo_state"]),
                    evidence_str.replace("|", "\\|"),
                ]
            )
            + " |"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--srs", default="docs/SRS.md")
    parser.add_argument("--todo", default="docs/TODO.md")
    parser.add_argument("--json-out", default="data/reports/srs_coverage/srs_coverage.json")
    parser.add_argument("--md-out", default="docs/SRS_COVERAGE_MATRIX.md")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    root = Path.cwd()
    srs_path = Path(args.srs)
    todo_path = Path(args.todo)
    json_out = Path(args.json_out)
    md_out = Path(args.md_out)

    requirements = parse_requirements(srs_path)
    todo_map = parse_todo_status(todo_path)

    excluded = {
        srs_path.resolve(),
        md_out.resolve(),
        json_out.resolve(),
        (Path("docs/SRS_GAP_BACKLOG.md")).resolve(),
    }
    evidence_map = build_evidence_index(root, excluded=excluded)

    rows: list[dict[str, object]] = []
    status_counts: Counter[str] = Counter()
    prefix_counts: dict[str, Counter[str]] = defaultdict(Counter)

    for req in requirements:
        todo_state = todo_map.get(req.req_id, TODOStatus()).state
        evidence_files = sorted(evidence_map.get(req.req_id, set()))
        status = classify(todo_state, evidence_files)
        row = {
            "id": req.req_id,
            "title": req.title,
            "prefix": req.prefix,
            "status": status,
            "todo_state": todo_state,
            "evidence_files": evidence_files,
        }
        rows.append(row)
        status_counts[status] += 1
        prefix_counts[req.prefix][status] += 1

    payload = {
        "summary": {
            "total": len(rows),
            "status_counts": dict(status_counts),
        },
        "rows": rows,
    }
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    write_markdown(
        out_path=md_out,
        rows=rows,
        status_counts=status_counts,
        prefix_counts=prefix_counts,
    )
    print(
        json.dumps(
            {
                "total": len(rows),
                "status_counts": dict(status_counts),
                "json_out": str(json_out),
                "md_out": str(md_out),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
