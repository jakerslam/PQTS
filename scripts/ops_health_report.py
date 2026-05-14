#!/usr/bin/env python3
"""Build an ops health report from the latest paper campaign snapshot."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path[:] = [str(SRC), *sys.path]
if str(ROOT) not in sys.path:
    sys.path[:] = [str(ROOT), *sys.path]

from analytics.ops_health import OpsThresholds, evaluate_operational_health


def _load_snapshot(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_snapshot(report_dir: Path) -> Path:
    candidates = sorted(report_dir.glob("paper_campaign_snapshot_*.json"))
    if not candidates:
        raise FileNotFoundError(f"No campaign snapshots found in {report_dir}")
    return candidates[-1]


def _write_report(out_dir: Path, payload: Dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"ops_health_{stamp}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", default="", help="Path to paper campaign snapshot JSON.")
    parser.add_argument("--reports-dir", default="data/reports")
    parser.add_argument("--out-dir", default="data/reports")
    parser.add_argument("--max-reject-rate", type=float, default=0.40)
    parser.add_argument("--max-p95-slippage-bps", type=float, default=20.0)
    parser.add_argument("--max-mape-pct", type=float, default=35.0)
    parser.add_argument("--max-degraded-venues", type=int, default=0)
    parser.add_argument("--max-calibration-alerts", type=int, default=0)
    parser.add_argument("--max-replay-quotes", type=int, default=0)
    parser.add_argument("--max-failover-quotes", type=int, default=0)
    parser.add_argument("--max-sanity-reject-quotes", type=int, default=0)
    parser.add_argument("--max-synthetic-quotes", type=int, default=0)
    parser.add_argument("--max-unresolved-quotes", type=int, default=0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report_dir = Path(args.reports_dir)
    snapshot_path = Path(args.snapshot) if args.snapshot else _latest_snapshot(report_dir)
    snapshot = _load_snapshot(snapshot_path)

    ops = evaluate_operational_health(
        campaign_stats=snapshot.get("stats", {}),
        readiness=snapshot.get("readiness", {}),
        reliability=snapshot.get("reliability", {}),
        calibration=snapshot.get("calibration", []),
        market_data_resilience=snapshot.get("market_data_resilience", {}),
        thresholds=OpsThresholds(
            max_reject_rate=float(args.max_reject_rate),
            max_p95_slippage_bps=float(args.max_p95_slippage_bps),
            max_mape_pct=float(args.max_mape_pct),
            max_degraded_venues=int(args.max_degraded_venues),
            max_calibration_alerts=int(args.max_calibration_alerts),
            max_replay_quotes=int(args.max_replay_quotes),
            max_failover_quotes=int(args.max_failover_quotes),
            max_sanity_reject_quotes=int(args.max_sanity_reject_quotes),
            max_synthetic_quotes=int(args.max_synthetic_quotes),
            max_unresolved_quotes=int(args.max_unresolved_quotes),
        ),
    )

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "snapshot": str(snapshot_path),
        "ops_health": ops,
    }
    path = _write_report(Path(args.out_dir), payload)
    print(path)
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
