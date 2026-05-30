#!/usr/bin/env python3
"""Build prediction-market microstructure replay feature artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path[:] = [str(SRC), *sys.path]
if str(ROOT) not in sys.path:
    sys.path[:] = [str(ROOT), *sys.path]

from research.prediction_market_replay import build_prediction_market_feature_artifact  # noqa: E402


def _parse_metadata(rows: list[str]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for row in rows:
        key, sep, raw_value = str(row).partition("=")
        if not sep or not key.strip():
            raise ValueError(f"metadata must be KEY=VALUE, got: {row}")
        value: Any = raw_value
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        metadata[key.strip()] = value
    return metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Replay raw prediction-market snapshots into features and a manifest.",
    )
    parser.add_argument("--raw-snapshots", required=True, help="Input raw snapshot JSONL path.")
    parser.add_argument("--features-out", required=True, help="Output feature JSONL path.")
    parser.add_argument("--manifest-out", required=True, help="Output replay manifest JSON path.")
    parser.add_argument("--source", required=True, help="Data source label, e.g. polymarket_ws.")
    parser.add_argument("--max-staleness-seconds", type=float, default=60.0)
    parser.add_argument("--wide-spread-threshold-bps", type=float, default=750.0)
    parser.add_argument("--min-rows", type=int, default=1)
    parser.add_argument(
        "--fail-on-quality-flags",
        action="store_true",
        help="Exit non-zero if any generated feature rows contain quality flags.",
    )
    parser.add_argument(
        "--metadata",
        action="append",
        default=[],
        help="Manifest metadata as KEY=VALUE. VALUE may be JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        metadata = _parse_metadata(list(args.metadata or []))
        manifest = build_prediction_market_feature_artifact(
            raw_snapshot_path=args.raw_snapshots,
            feature_snapshot_path=args.features_out,
            manifest_path=args.manifest_out,
            source=args.source,
            max_staleness_seconds=float(args.max_staleness_seconds),
            wide_spread_threshold_bps=float(args.wide_spread_threshold_bps),
            metadata=metadata,
        )
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1

    payload = manifest.to_dict()
    payload["ok"] = True
    gate_failures: list[str] = []
    if int(manifest.row_count) < int(args.min_rows):
        gate_failures.append("row_count_below_minimum")
    if args.fail_on_quality_flags and manifest.quality_flag_counts:
        gate_failures.append("quality_flags_present")
    payload["gate_failures"] = gate_failures
    print(json.dumps(payload, sort_keys=True))
    return 2 if gate_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
