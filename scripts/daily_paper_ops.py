#!/usr/bin/env python3
"""Daily paper-ops wrapper: run campaign slice then readiness report."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent


def _parse_json_from_output(output: str) -> Dict[str, Any]:
    for line in reversed(output.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            continue
    return {}


def _build_campaign_cmd(args: argparse.Namespace) -> List[str]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_paper_campaign.py"),
        "--config",
        args.config,
        "--cycles",
        str(int(args.campaign_cycles)),
        "--sleep-seconds",
        str(float(args.campaign_sleep_seconds)),
        "--notional-usd",
        str(float(args.campaign_notional_usd)),
        "--readiness-every",
        str(int(args.campaign_readiness_every)),
        "--out-dir",
        args.out_dir,
        "--lookback-days",
        str(int(args.lookback_days)),
        "--min-days",
        str(int(args.min_days)),
        "--min-fills",
        str(int(args.min_fills)),
        "--max-p95-slippage-bps",
        str(float(args.max_p95_slippage_bps)),
        "--max-mape-pct",
        str(float(args.max_mape_pct)),
        "--paper-base-slippage-bps",
        str(float(args.paper_base_slippage_bps)),
        "--paper-min-slippage-bps",
        str(float(args.paper_min_slippage_bps)),
        "--paper-stress-multiplier",
        str(float(args.paper_stress_multiplier)),
    ]
    if args.campaign_symbols:
        cmd.extend(["--symbols", args.campaign_symbols])
    return cmd


def _build_readiness_cmd(args: argparse.Namespace) -> List[str]:
    return [
        sys.executable,
        str(ROOT / "scripts" / "paper_readiness_report.py"),
        "--tca-db",
        args.tca_db,
        "--lookback-days",
        str(int(args.lookback_days)),
        "--min-days",
        str(int(args.min_days)),
        "--min-fills",
        str(int(args.min_fills)),
        "--max-p95-slippage-bps",
        str(float(args.max_p95_slippage_bps)),
        "--max-mape-pct",
        str(float(args.max_mape_pct)),
        "--out-dir",
        args.out_dir,
    ]


def _run(cmd: List[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(ROOT), check=True, capture_output=True, text=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/paper.yaml")
    parser.add_argument("--campaign-symbols", default="BTCUSDT,ETHUSDT,BTC-USD,ETH-USD")
    parser.add_argument("--campaign-cycles", type=int, default=1440)
    parser.add_argument("--campaign-sleep-seconds", type=float, default=60.0)
    parser.add_argument("--campaign-notional-usd", type=float, default=150.0)
    parser.add_argument("--campaign-readiness-every", type=int, default=60)
    parser.add_argument("--paper-base-slippage-bps", type=float, default=8.0)
    parser.add_argument("--paper-min-slippage-bps", type=float, default=1.0)
    parser.add_argument("--paper-stress-multiplier", type=float, default=1.5)
    parser.add_argument("--tca-db", default="data/tca_records.csv")
    parser.add_argument("--lookback-days", type=int, default=60)
    parser.add_argument("--min-days", type=int, default=30)
    parser.add_argument("--min-fills", type=int, default=200)
    parser.add_argument("--max-p95-slippage-bps", type=float, default=20.0)
    parser.add_argument("--max-mape-pct", type=float, default=35.0)
    parser.add_argument("--out-dir", default="data/reports")
    parser.add_argument("--skip-campaign", action="store_true")
    parser.add_argument("--require-ready", action="store_true")
    return parser


def _write_summary(out_dir: Path, summary: Dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"daily_paper_ops_{stamp}.json"
    path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main() -> int:
    args = build_parser().parse_args()

    campaign_payload: Dict[str, Any] = {}
    if not args.skip_campaign:
        campaign_cmd = _build_campaign_cmd(args)
        campaign_run = _run(campaign_cmd)
        campaign_payload = _parse_json_from_output(campaign_run.stdout)
        print(campaign_run.stdout, end="")

    readiness_cmd = _build_readiness_cmd(args)
    readiness_run = _run(readiness_cmd)
    readiness_payload = _parse_json_from_output(readiness_run.stdout)
    print(readiness_run.stdout, end="")

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "campaign": campaign_payload,
        "readiness": readiness_payload,
    }
    summary_path = _write_summary(Path(args.out_dir), summary)
    print(summary_path)

    if args.require_ready and not bool(readiness_payload.get("ready_for_canary", False)):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
