#!/usr/bin/env python3
"""Summarize live-data paper soak artifacts with data-quality diagnostics."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict


def _latest_snapshot(report_dir: Path) -> Path:
    candidates = sorted(report_dir.glob("paper_campaign_snapshot_*.json"))
    if not candidates:
        raise FileNotFoundError(f"No paper campaign snapshots found in {report_dir}")
    return candidates[-1]


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _price_ranges(tca_path: Path) -> Dict[str, Dict[str, float | int]]:
    if not tca_path.exists():
        return {}

    ranges: Dict[str, Dict[str, float | int]] = {}
    with tca_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            symbol = str(row.get("symbol", "")).strip()
            if not symbol:
                continue
            try:
                price = float(row.get("price", 0.0) or 0.0)
            except (TypeError, ValueError):
                continue
            if price <= 0.0:
                continue
            current = ranges.setdefault(
                symbol,
                {"trades": 0, "min_price": price, "max_price": price},
            )
            current["trades"] = int(current["trades"]) + 1
            current["min_price"] = min(float(current["min_price"]), price)
            current["max_price"] = max(float(current["max_price"]), price)
    return ranges


def build_report(*, snapshot_path: Path, tca_path: Path | None = None) -> Dict[str, Any]:
    snapshot = _load_json(snapshot_path)
    alpha_source = str(snapshot.get("campaign_expected_alpha_source", ""))
    market_data = snapshot.get("market_data_resilience", {}) or {}
    md_metrics = dict(market_data.get("metrics", {}) or {})
    ops_summary = (snapshot.get("ops_health", {}) or {}).get("summary", {}) or {}
    tca_ranges = _price_ranges(tca_path) if tca_path is not None else {}

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "snapshot": str(snapshot_path),
        "tca_path": str(tca_path) if tca_path is not None else "",
        "stats": snapshot.get("stats", {}),
        "readiness": snapshot.get("readiness", {}),
        "promotion_decision": (snapshot.get("promotion_gate", {}) or {}).get("decision", ""),
        "ops_summary": ops_summary,
        "market_data_resilience": market_data,
        "price_ranges": tca_ranges,
        "simulation_only_alpha_override": alpha_source == "cli_override",
        "data_quality_incidents": {
            "replay_quotes": int(md_metrics.get("replay_quotes", 0) or 0),
            "failover_quotes": int(md_metrics.get("failover_quotes", 0) or 0),
            "sanity_reject_quotes": int(md_metrics.get("sanity_reject_quotes", 0) or 0),
            "synthetic_quotes": int(md_metrics.get("synthetic_quotes", 0) or 0),
            "unresolved_quotes": int(md_metrics.get("unresolved_quotes", 0) or 0),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", default="")
    parser.add_argument("--reports-dir", default="data/reports")
    parser.add_argument("--tca-path", default="")
    parser.add_argument("--out-dir", default="data/reports")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    snapshot_path = Path(args.snapshot) if args.snapshot else _latest_snapshot(Path(args.reports_dir))
    tca_path = Path(args.tca_path) if str(args.tca_path or "").strip() else None
    payload = build_report(snapshot_path=snapshot_path, tca_path=tca_path)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"live_data_soak_report_{stamp}.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(out_path)
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
