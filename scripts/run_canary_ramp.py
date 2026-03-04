#!/usr/bin/env python3
"""Evaluate canary capital ramp and persist allocation step with rollback policy."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from execution.canary_ramp import (  # noqa: E402
    CanaryRampController,
    CanaryRampMetrics,
    CanaryRampPolicy,
)


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return payload


def _latest(path: Path, pattern: str) -> Path:
    rows = sorted(path.glob(pattern))
    if not rows:
        raise FileNotFoundError(f"No files found in {path} for pattern {pattern}")
    return rows[-1]


def _parse_dt(value: str) -> datetime:
    token = str(value).replace("Z", "+00:00")
    dt = datetime.fromisoformat(token)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports-dir", default="data/reports")
    parser.add_argument("--campaign-snapshot", default="")
    parser.add_argument("--slo-health", default="")
    parser.add_argument("--state-path", default="data/analytics/canary_ramp_state.json")
    parser.add_argument("--out-dir", default="data/reports")
    parser.add_argument("--steps", default="0.01,0.02,0.05,0.10")
    parser.add_argument("--min-days-per-step", type=int, default=14)
    parser.add_argument("--max-reject-rate", type=float, default=0.05)
    parser.add_argument("--max-slippage-mape-pct", type=float, default=25.0)
    parser.add_argument("--max-critical-alerts", type=int, default=0)
    parser.add_argument("--max-reconciliation-incidents", type=int, default=0)
    return parser


def _parse_steps(value: str) -> list[float]:
    steps = [float(token.strip()) for token in value.split(",") if token.strip()]
    if not steps:
        raise ValueError("--steps must include at least one numeric allocation fraction")
    return steps


def main() -> int:
    args = build_parser().parse_args()
    reports_dir = Path(args.reports_dir)
    campaign_path = (
        Path(args.campaign_snapshot)
        if args.campaign_snapshot
        else _latest(reports_dir, "paper_campaign_snapshot_*.json")
    )
    slo_path = (
        Path(args.slo_health) if args.slo_health else _latest(reports_dir, "slo_health_*.json")
    )

    campaign = _load_json(campaign_path)
    slo = _load_json(slo_path)

    policy = CanaryRampPolicy(
        steps=_parse_steps(args.steps),
        min_days_per_step=int(args.min_days_per_step),
        max_reject_rate=float(args.max_reject_rate),
        max_slippage_mape_pct=float(args.max_slippage_mape_pct),
        max_critical_alerts=int(args.max_critical_alerts),
        max_reconciliation_incidents=int(args.max_reconciliation_incidents),
    )
    controller = CanaryRampController(state_path=str(args.state_path), policy=policy)

    state = controller.load_state()
    now = datetime.now(timezone.utc)
    transition_at = _parse_dt(state.last_transition_at)
    days_in_step = max((now - transition_at).days, 0)

    readiness = campaign.get("readiness", {}) if isinstance(campaign.get("readiness"), dict) else {}
    stats = campaign.get("stats", {}) if isinstance(campaign.get("stats"), dict) else {}
    ops_health = (
        campaign.get("ops_health", {}) if isinstance(campaign.get("ops_health"), dict) else {}
    )
    ops_summary = (
        ops_health.get("summary", {}) if isinstance(ops_health.get("summary"), dict) else {}
    )

    slo_health = slo.get("slo_health", {}) if isinstance(slo.get("slo_health"), dict) else {}
    slo_metrics = (
        slo_health.get("metrics", {}) if isinstance(slo_health.get("metrics"), dict) else {}
    )
    reconciliation_incidents = int(slo_metrics.get("reconciliation_incidents", 0))

    metrics = CanaryRampMetrics(
        days_in_step=days_in_step,
        reject_rate=float(stats.get("reject_rate", 0.0)),
        slippage_mape_pct=float(readiness.get("slippage_mape_pct", 0.0)),
        critical_alerts=int(ops_summary.get("critical", 0)),
        reconciliation_incidents=reconciliation_incidents,
        kill_switch_triggered=bool(stats.get("kill_switch_active", False)),
    )
    decision = controller.evaluate_and_persist(metrics=metrics)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "campaign_snapshot": str(campaign_path),
        "slo_health": str(slo_path),
        "decision": decision,
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = out_dir / f"canary_ramp_{stamp}.json"
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    payload["report_path"] = str(report_path)

    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
