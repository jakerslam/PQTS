#!/usr/bin/env python3
"""Validate Studio casual UX and template-first contracts (COMP-7, COMP-12)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.append(str(SRC_ROOT))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quickstart", default="docs/QUICKSTART_5_MIN.md")
    parser.add_argument("--first-success-cli", default="src/app/first_success_cli.py")
    return parser


def _list_subcommands(parser) -> set[str]:
    out: set[str] = set()
    for action in parser._actions:  # noqa: SLF001
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            out.update(action.choices.keys())
    return out


def main() -> int:
    from app.first_success_cli import build_first_success_parser

    args = build_arg_parser().parse_args()
    parser = build_first_success_parser()
    subcommands = _list_subcommands(parser)
    required = {"init", "demo", "backtest", "paper"}
    missing = sorted(required.difference(subcommands))
    if missing:
        raise SystemExit(f"missing first-success subcommands: {missing}")

    first_success_text = Path(args.first_success_cli).read_text(encoding="utf-8")
    required_snippets = [
        "template_run_",
        "template_run_diff_",
        "studio_explanation",
        "why_blocked_hint",
    ]
    missing_snippets = [token for token in required_snippets if token not in first_success_text]
    if missing_snippets:
        raise SystemExit(f"missing template/ux snippets in first-success CLI: {missing_snippets}")

    quickstart = Path(args.quickstart).read_text(encoding="utf-8")
    for command in ("pqts init", "pqts demo", "pqts backtest momentum", "pqts paper start"):
        if command not in quickstart:
            raise SystemExit(f"quickstart missing command: {command}")

    payload = {
        "validated": True,
        "subcommands": sorted(subcommands),
        "required_commands": sorted(required),
    }
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
