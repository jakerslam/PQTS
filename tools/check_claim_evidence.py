#!/usr/bin/env python3
"""Check benchmark claim blocks for explicit evidence and trust classification tags."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable


def _default_targets() -> list[str]:
    return [
        "docs/BENCHMARKS.md",
        "results/*/README.md",
    ]


def _expand_targets(patterns: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        if any(token in pattern for token in ["*", "?", "["]):
            files.extend(sorted(Path(".").glob(pattern)))
            continue
        path = Path(pattern)
        if path.exists():
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


def _has_required_tags(text: str) -> bool:
    content = text.lower()
    has_class = (
        "result_class" in content
        or "result class" in content
        or "claim class" in content
        or "reference" in content
        or "diagnostic_only" in content
        or "unverified" in content
    )
    has_evidence = (
        "## command" in content
        or "```bash" in content
        or "provenance" in content
        or "simulation_suite_" in content
    )
    return has_class and has_evidence


def evaluate_claim_evidence(files: Iterable[Path]) -> list[str]:
    errors: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        if not _has_required_tags(text):
            errors.append(
                f"{path}: missing explicit claim classification and/or evidence markers"
            )
    return errors


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        action="append",
        default=[],
        help="Target file or glob. Can be passed multiple times.",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    patterns = args.target if args.target else _default_targets()
    files = _expand_targets(patterns)
    if not files:
        print("FAIL no files matched target patterns")
        return 2
    errors = evaluate_claim_evidence(files)
    if errors:
        for item in errors:
            print(f"FAIL {item}")
        print(f"Checked {len(files)} files: {len(errors)} violation(s).")
        return 2
    print(f"PASS claim-evidence checks: {len(files)} files validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
