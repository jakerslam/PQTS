#!/usr/bin/env python3
"""Generate monthly benchmark report artifacts from reproducible result bundles."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if SRC.exists():
    src_str = str(SRC)
    if src_str not in sys.path:
        sys.path[:] = [src_str, *sys.path]
if str(ROOT) not in sys.path:
    sys.path[:] = [str(ROOT), *sys.path]

from analytics.monthly_report_pipeline import generate_monthly_report_artifacts  # noqa: E402


def _default_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--out-dir", default="data/reports/monthly")
    parser.add_argument("--month", default=_default_month(), help="Target month in YYYY-MM format")
    parser.add_argument("--starting-equity", type=float, default=10_000.0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    artifacts = generate_monthly_report_artifacts(
        results_dir=str(args.results_dir),
        output_dir=str(args.out_dir),
        month=str(args.month),
        starting_equity=float(args.starting_equity),
    )

    payload = {
        "month": artifacts.report.month,
        "bundle_count": artifacts.report.bundle_count,
        "scenario_count": artifacts.report.scenario_count,
        "json_path": str(artifacts.json_path),
        "html_path": str(artifacts.html_path),
        "pdf_path": str(artifacts.pdf_path),
        "equity_curve_svg_path": str(artifacts.equity_curve_svg_path),
    }
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
