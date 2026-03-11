#!/usr/bin/env python3
"""Validate freshness of competitor source references."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.append(str(SRC_ROOT))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", default="config/moat/competitor_sources.json")
    parser.add_argument("--max-age-days", type=int, default=30)
    parser.add_argument("--today", default="")
    return parser


def main() -> int:
    from moat.competitor_revalidation import CompetitorSource, evaluate_source_freshness

    args = build_arg_parser().parse_args()
    payload = json.loads(Path(args.sources).read_text(encoding="utf-8"))
    rows = [CompetitorSource(**item) for item in payload.get("sources", [])]
    today = date.fromisoformat(args.today) if args.today else date.today()

    report = evaluate_source_freshness(
        sources=rows,
        today=today,
        max_age_days=int(args.max_age_days),
    )
    if not report["passed"]:
        raise SystemExit(json.dumps(report, sort_keys=True))
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
