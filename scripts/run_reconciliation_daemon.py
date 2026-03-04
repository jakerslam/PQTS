#!/usr/bin/env python3
"""Run reconciliation daemon and auto-halt router when mismatches breach policy."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from execution.reconciliation_daemon import ReconciliationConfig, ReconciliationDaemon  # noqa: E402
from execution.risk_aware_router import RiskAwareRouter  # noqa: E402
from risk.kill_switches import RiskLimits  # noqa: E402


def _load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _pct(value: Any, default: float) -> float:
    if value is None:
        return float(default)
    token = float(value)
    return token / 100.0 if token > 1.0 else token


def _build_risk_limits(config: Dict[str, Any]) -> RiskLimits:
    risk_cfg = config.get("risk", {})
    return RiskLimits(
        max_daily_loss_pct=_pct(
            risk_cfg.get("max_daily_loss_pct", risk_cfg.get("max_portfolio_risk_pct", 2.0)),
            0.02,
        ),
        max_drawdown_pct=_pct(risk_cfg.get("max_drawdown_pct", 0.15), 0.15),
        max_gross_leverage=float(risk_cfg.get("max_leverage", 2.0)),
        max_order_notional=float(risk_cfg.get("max_order_notional", 50000.0)),
        max_participation=_pct(risk_cfg.get("max_participation", 0.05), 0.05),
        max_slippage_bps=float(risk_cfg.get("max_slippage_bps", 50.0)),
    )


def _build_broker_config(config: Dict[str, Any], *, tca_db: str) -> Dict[str, Any]:
    risk_cfg = config.get("risk", {})
    execution_cfg = config.get("execution", {})
    return {
        "enabled": True,
        "live_execution": False,
        "max_symbol_notional": risk_cfg.get("max_symbol_notional", {}),
        "max_venue_notional": risk_cfg.get("max_venue_notional", {}),
        "tca_db_path": str(tca_db),
        "exchanges": {},
        "max_single_order_size": execution_cfg.get("max_single_order_size", 1.0),
        "twap_interval_seconds": execution_cfg.get("twap_interval_seconds", 60),
        "prefer_maker": execution_cfg.get("prefer_maker", True),
        "default_monthly_volume_usd": execution_cfg.get("default_monthly_volume_usd", 0.0),
        "monthly_volume_by_venue": execution_cfg.get("monthly_volume_by_venue", {}),
        "fee_tiers": execution_cfg.get("fee_tiers", {}),
        "default_maker_fee_bps": execution_cfg.get("default_maker_fee_bps", 10.0),
        "default_taker_fee_bps": execution_cfg.get("default_taker_fee_bps", 12.0),
        "reliability": execution_cfg.get("reliability", {}),
        "regime_overlay": execution_cfg.get("regime_overlay", {}),
    }


def _parse_aliases(value: str) -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    for token in value.split(","):
        row = token.strip()
        if not row or ":" not in row:
            continue
        source, target = row.split(":", 1)
        if source.strip() and target.strip():
            aliases[source.strip()] = target.strip()
    return aliases


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/paper.yaml")
    parser.add_argument("--cycles", type=int, default=10)
    parser.add_argument("--sleep-seconds", type=float, default=5.0)
    parser.add_argument("--tca-db", default="data/tca_records.csv")
    parser.add_argument("--incident-log", default="data/analytics/reconciliation_incidents.jsonl")
    parser.add_argument("--out-dir", default="data/reports")
    parser.add_argument("--tolerance", type=float, default=1e-6)
    parser.add_argument("--max-mismatched-symbols", type=int, default=0)
    halt_group = parser.add_mutually_exclusive_group()
    halt_group.add_argument("--halt-on-mismatch", dest="halt_on_mismatch", action="store_true")
    halt_group.add_argument(
        "--no-halt-on-mismatch",
        dest="halt_on_mismatch",
        action="store_false",
    )
    parser.set_defaults(halt_on_mismatch=True)
    parser.add_argument(
        "--symbol-aliases",
        default="",
        help="Comma-separated map of source:target symbols, ex BTCUSDT:BTC-USD",
    )
    return parser


async def _run(args: argparse.Namespace) -> Dict[str, Any]:
    config = _load_yaml(args.config)
    router = RiskAwareRouter(
        risk_config=_build_risk_limits(config),
        broker_config=_build_broker_config(config, tca_db=args.tca_db),
        tca_db_path=str(args.tca_db),
    )
    capital = float(config.get("risk", {}).get("initial_capital", 10000.0))
    router.set_capital(capital, source="reconciliation_daemon")
    router.configure_market_adapters(config.get("markets", {}))
    await router.start_market_data()

    daemon = ReconciliationDaemon(
        router=router,
        config=ReconciliationConfig(
            tolerance=float(args.tolerance),
            max_mismatched_symbols=int(args.max_mismatched_symbols),
            halt_on_mismatch=bool(args.halt_on_mismatch),
            symbol_aliases=_parse_aliases(args.symbol_aliases),
        ),
        incident_log_path=str(args.incident_log),
    )

    try:
        cycles = await daemon.run_loop(
            cycles=max(int(args.cycles), 0),
            sleep_seconds=float(args.sleep_seconds),
            stop_on_halt=True,
        )
    finally:
        await router.stop_market_data()

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cycles": cycles,
        "incident_log": str(daemon.incident_log_path),
        "halted": bool(router.risk_engine.is_halted),
    }
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    report_path = out_dir / f"reconciliation_daemon_{stamp}.json"
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    payload["report_path"] = str(report_path)
    return payload


def main() -> int:
    args = build_parser().parse_args()
    payload = asyncio.run(_run(args))
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
