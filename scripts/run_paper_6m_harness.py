#!/usr/bin/env python3
"""Run a six-month paper-trading harness via monthly campaign slices."""

from __future__ import annotations

import argparse
import calendar
import json
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent


def _parse_json_from_output(output: str) -> Dict[str, Any]:
    for line in reversed(output.splitlines()):
        token = line.strip()
        if not token:
            continue
        try:
            payload = json.loads(token)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def _parse_date(token: str) -> date:
    return datetime.strptime(str(token).strip(), "%Y-%m-%d").date()


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + int(months)
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def build_month_windows(*, anchor_date: date, months: int) -> List[Tuple[date, date]]:
    if int(months) <= 0:
        raise ValueError("months must be >= 1")
    start = _add_months(anchor_date, -int(months))
    windows: List[Tuple[date, date]] = []
    current = start
    for _ in range(int(months)):
        nxt = _add_months(current, 1)
        windows.append((current, nxt))
        current = nxt
    return windows


def _run(cmd: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [str(item) for item in cmd],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )


def _build_campaign_cmd(
    *,
    args: argparse.Namespace,
    out_dir: Path,
    tca_db_path: Path,
) -> List[str]:
    readiness_every = int(args.readiness_every)
    if readiness_every <= 0:
        readiness_every = max(1, int(args.cycles_per_month) // 3)

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_paper_campaign.py"),
        "--config",
        str(args.config),
        "--cycles",
        str(int(args.cycles_per_month)),
        "--sleep-seconds",
        str(float(args.sleep_seconds)),
        "--notional-usd",
        str(float(args.notional_usd)),
        "--readiness-every",
        str(int(readiness_every)),
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
        "--max-reject-rate",
        str(float(args.max_reject_rate)),
        "--out-dir",
        str(out_dir),
        "--tca-db-path",
        str(tca_db_path),
    ]
    symbols = str(args.symbols).strip()
    if symbols:
        cmd.extend(["--symbols", symbols])
    risk_profile = str(args.risk_profile).strip()
    if risk_profile:
        cmd.extend(["--risk-profile", risk_profile])
    operator_tier = str(args.operator_tier).strip()
    if operator_tier:
        cmd.extend(["--operator-tier", operator_tier])
    return cmd


def _summarize_month(
    *,
    index: int,
    window: Tuple[date, date],
    payload: Dict[str, Any],
    out_dir: Path,
) -> Dict[str, Any]:
    readiness = payload.get("readiness", {}) if isinstance(payload.get("readiness"), dict) else {}
    promotion = (
        payload.get("promotion_gate", {})
        if isinstance(payload.get("promotion_gate"), dict)
        else {}
    )
    ops_summary = (
        (payload.get("ops_health", {}) or {}).get("summary", {})
        if isinstance(payload.get("ops_health"), dict)
        else {}
    )

    start, end_exclusive = window
    end_inclusive = end_exclusive - timedelta(days=1)
    return {
        "month_index": int(index),
        "window_start": start.isoformat(),
        "window_end": end_inclusive.isoformat(),
        "window_end_exclusive": end_exclusive.isoformat(),
        "submitted": int(payload.get("submitted", 0)),
        "filled": int(payload.get("filled", 0)),
        "rejected": int(payload.get("rejected", 0)),
        "reject_rate": float(payload.get("reject_rate", 0.0)),
        "ready_for_canary": bool(readiness.get("ready_for_canary", False)),
        "promotion_decision": str(promotion.get("decision", "unknown")),
        "ops_critical_alerts": int(ops_summary.get("critical", 0)),
        "slice_out_dir": str(out_dir),
    }


def _aggregate(
    *,
    monthly: Sequence[Dict[str, Any]],
    max_avg_reject_rate: float,
    min_ready_months: int,
) -> Dict[str, Any]:
    total_submitted = sum(int(row.get("submitted", 0)) for row in monthly)
    total_filled = sum(int(row.get("filled", 0)) for row in monthly)
    total_rejected = sum(int(row.get("rejected", 0)) for row in monthly)
    avg_reject_rate = (float(total_rejected) / float(total_submitted)) if total_submitted > 0 else 0.0
    ready_months = sum(1 for row in monthly if bool(row.get("ready_for_canary", False)))

    promotion_counts: Dict[str, int] = {}
    for row in monthly:
        decision = str(row.get("promotion_decision", "unknown"))
        promotion_counts[decision] = int(promotion_counts.get(decision, 0)) + 1

    checks = {
        "submitted_each_month": all(int(row.get("submitted", 0)) > 0 for row in monthly),
        "avg_reject_rate_within_limit": avg_reject_rate <= float(max_avg_reject_rate),
        "minimum_ready_months": ready_months >= int(min_ready_months),
    }
    return {
        "months": len(monthly),
        "total_submitted": int(total_submitted),
        "total_filled": int(total_filled),
        "total_rejected": int(total_rejected),
        "avg_reject_rate": float(avg_reject_rate),
        "ready_months": int(ready_months),
        "promotion_decisions": promotion_counts,
        "checks": checks,
        "passed": all(bool(v) for v in checks.values()),
    }


def _write_report(out_dir: Path, payload: Dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"paper_6m_harness_{stamp}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/paper.yaml")
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument(
        "--anchor-date",
        default="",
        help="Window anchor date (inclusive upper bound) in YYYY-MM-DD. Default: today UTC.",
    )
    parser.add_argument("--cycles-per-month", type=int, default=12)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--notional-usd", type=float, default=150.0)
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT,BTC-USD,ETH-USD")
    parser.add_argument("--risk-profile", default="balanced")
    parser.add_argument("--operator-tier", default="")
    parser.add_argument("--lookback-days", type=int, default=60)
    parser.add_argument("--min-days", type=int, default=1)
    parser.add_argument("--min-fills", type=int, default=10)
    parser.add_argument("--readiness-every", type=int, default=0)
    parser.add_argument("--max-p95-slippage-bps", type=float, default=25.0)
    parser.add_argument("--max-mape-pct", type=float, default=40.0)
    parser.add_argument("--max-reject-rate", type=float, default=0.5)
    parser.add_argument("--max-avg-reject-rate", type=float, default=0.5)
    parser.add_argument("--min-ready-months", type=int, default=1)
    parser.add_argument("--strict", action="store_true", help="Return non-zero when aggregate checks fail.")
    parser.add_argument("--out-dir", default="data/reports/paper_6m")
    parser.add_argument("--tca-root", default="data/tca/paper_6m")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    anchor = _parse_date(args.anchor_date) if str(args.anchor_date).strip() else datetime.now(timezone.utc).date()
    windows = build_month_windows(anchor_date=anchor, months=int(args.months))

    out_dir = Path(args.out_dir)
    tca_root = Path(args.tca_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    tca_root.mkdir(parents=True, exist_ok=True)

    monthly: List[Dict[str, Any]] = []
    for idx, window in enumerate(windows, start=1):
        start, end_exclusive = window
        label = f"month_{idx:02d}_{start.isoformat()}_{(end_exclusive - timedelta(days=1)).isoformat()}"
        month_dir = out_dir / label
        month_tca = tca_root / f"paper_6m_month_{idx:02d}.csv"

        cmd = _build_campaign_cmd(args=args, out_dir=month_dir, tca_db_path=month_tca)
        run = _run(cmd)
        payload = _parse_json_from_output(run.stdout)
        if not payload:
            raise RuntimeError(f"Unable to parse campaign payload for {label}")

        month_summary = _summarize_month(index=idx, window=window, payload=payload, out_dir=month_dir)
        monthly.append(month_summary)
        print(
            json.dumps(
                {
                    "month_index": idx,
                    "window_start": month_summary["window_start"],
                    "window_end": month_summary["window_end"],
                    "submitted": month_summary["submitted"],
                    "filled": month_summary["filled"],
                    "reject_rate": month_summary["reject_rate"],
                    "promotion_decision": month_summary["promotion_decision"],
                },
                sort_keys=True,
            )
        )

    aggregate = _aggregate(
        monthly=monthly,
        max_avg_reject_rate=float(args.max_avg_reject_rate),
        min_ready_months=int(args.min_ready_months),
    )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "harness": {
            "months": int(args.months),
            "anchor_date": anchor.isoformat(),
            "config": str(args.config),
            "cycles_per_month": int(args.cycles_per_month),
            "symbols": [token.strip() for token in str(args.symbols).split(",") if token.strip()],
            "risk_profile": str(args.risk_profile),
        },
        "monthly": monthly,
        "aggregate": aggregate,
    }
    report_path = _write_report(out_dir=out_dir, payload=report)

    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "months": int(args.months),
                "passed": bool(aggregate.get("passed", False)),
                "total_submitted": int(aggregate.get("total_submitted", 0)),
                "total_filled": int(aggregate.get("total_filled", 0)),
                "avg_reject_rate": float(aggregate.get("avg_reject_rate", 0.0)),
                "ready_months": int(aggregate.get("ready_months", 0)),
            },
            sort_keys=True,
        )
    )

    if bool(args.strict) and not bool(aggregate.get("passed", False)):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
