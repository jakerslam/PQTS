#!/usr/bin/env python3
"""Validate that performance/precision claims include nearby evidence links."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

_CLAIM_KEYWORDS = (
    "sharpe",
    "drawdown",
    "max-dd",
    "fill",
    "reject",
    "precision",
    "win rate",
    "roi",
    "quality",
)
_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
_RESULT_PATH_HINTS = ("results/", "data/reports/", "docs/REFERENCE_PERFORMANCE.md")
_PERF_SECTION_HINTS = ("performance", "benchmark", "results", "reference", "proof")


def _is_claim_line(line: str) -> bool:
    lowered = line.lower()
    if not any(keyword in lowered for keyword in _CLAIM_KEYWORDS):
        return False
    return bool(re.search(r"\d", line))


def _window_has_evidence_link(lines: list[str], idx: int) -> bool:
    start = max(0, idx - 6)
    end = min(idx + 7, len(lines))
    window = lines[start:end]
    for item in window:
        for match in _LINK_RE.findall(item):
            target = str(match)
            if any(hint in target for hint in _RESULT_PATH_HINTS):
                return True
    return False


def evaluate_claim_evidence_links(paths: Iterable[Path]) -> list[str]:
    errors: list[str] = []
    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        current_heading = ""
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#"):
                current_heading = stripped.lstrip("#").strip().lower()
            if not _is_claim_line(line):
                continue
            if current_heading and not any(token in current_heading for token in _PERF_SECTION_HINTS):
                continue
            if _window_has_evidence_link(lines, idx):
                continue
            errors.append(
                f"{path}:{idx + 1} claim appears without nearby evidence link to results/report artifacts"
            )
    return errors


def _expand_targets(patterns: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        path = Path(pattern)
        if any(token in pattern for token in ("*", "?", "[")):
            files.extend(sorted(Path(".").glob(pattern)))
        elif path.exists():
            files.append(path)
    dedup: list[Path] = []
    seen: set[Path] = set()
    for file in files:
        resolved = file.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        dedup.append(file)
    return dedup


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        action="append",
        default=[],
        help="Target file/glob (repeatable). Defaults to README/benchmark/reference docs.",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    patterns = args.target or ["README.md", "docs/BENCHMARKS.md", "docs/REFERENCE_PERFORMANCE.md"]
    files = _expand_targets(patterns)
    if not files:
        print("FAIL no files matched target patterns")
        return 2
    errors = evaluate_claim_evidence_links(files)
    if errors:
        for error in errors:
            print(f"FAIL {error}")
        print(f"Claim-evidence-link validation failed: {len(errors)} issue(s)")
        return 2
    print(f"PASS claim-evidence-link validation: {len(files)} files checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
