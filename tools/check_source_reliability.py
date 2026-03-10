#!/usr/bin/env python3
"""Validate source reliability and claim-handling markers (LANG-12, PMKT-15, MOAT-13)."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

CLASS_TOKENS = ("observed", "inferred", "unverified")
PERF_KEYWORDS = (
    "sharpe",
    "pnl",
    "return",
    "profit",
    "win rate",
    "cagr",
    "alpha",
)
CLASS_RE = re.compile(r"\b(observed|inferred|unverified|reference|diagnostic_only|verified)\b", re.I)
URL_RE = re.compile(r"https?://", re.I)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        action="append",
        default=[],
        help="File path to validate. Can be repeated.",
    )
    return parser


def _default_targets() -> list[Path]:
    return [
        Path("docs/SRS.md"),
        Path("docs/BENCHMARKS.md"),
    ]


def _iter_targets(items: Iterable[str]) -> list[Path]:
    if not items:
        return [path for path in _default_targets() if path.exists()]
    out: list[Path] = []
    for token in items:
        path = Path(token)
        if path.exists():
            out.append(path)
    return out


def _has_perf_keyword(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in PERF_KEYWORDS)


def _validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    lowered = text.lower()

    # Require global taxonomy terms in SRS.
    if path.name == "SRS.md":
        for token in CLASS_TOKENS:
            if token not in lowered:
                errors.append(f"{path}: missing taxonomy token '{token}'")

    paragraphs = [chunk.strip() for chunk in re.split(r"\n\s*\n", text) if chunk.strip()]
    for idx, block in enumerate(paragraphs, start=1):
        if not _has_perf_keyword(block):
            continue
        if not URL_RE.search(block):
            continue
        if not CLASS_RE.search(block):
            errors.append(
                f"{path}: paragraph {idx} has performance/source claim without trust classification"
            )
    return errors


def main() -> int:
    args = build_arg_parser().parse_args()
    targets = _iter_targets(args.target)
    if not targets:
        print("FAIL no target files found")
        return 2

    errors: list[str] = []
    for path in targets:
        errors.extend(_validate_file(path))

    if errors:
        for item in errors:
            print(f"FAIL {item}")
        print(f"Checked {len(targets)} files: {len(errors)} violation(s).")
        return 2

    print(f"PASS source reliability checks: {len(targets)} files validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
