#!/usr/bin/env python3
"""Run continuous paper-trading campaign and emit readiness snapshots."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.ops_health import OpsThresholds, evaluate_operational_health  # noqa: E402
from analytics.promotion_gates import (  # noqa: E402
    PromotionGateThresholds,
    evaluate_promotion_gate,
)
from analytics.revenue_diagnostics import RevenueDiagnostics  # noqa: E402
from core.operator_tier import resolve_operator_tier, validate_operator_tier_overrides  # noqa: E402
from execution.paper_campaign import (  # noqa: E402
    CampaignStats,
    build_portfolio_snapshot,
    build_probe_order,
    iter_cycle_symbols,
    select_symbol_price,
)
from execution.paper_fill_model import (  # noqa: E402
    MicrostructurePaperFillProvider,
    PaperFillModelConfig,
)
from execution.risk_aware_router import RiskAwareRouter  # noqa: E402
from execution.smart_router import OrderType  # noqa: E402
from risk.kill_switches import RiskLimits  # noqa: E402
from risk.risk_tolerance import (  # noqa: E402
    resolve_effective_risk_config,
    risk_profile_payload,
)


def _parse_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data


def _pct(value: Any, default: float) -> float:
    if value is None:
        return default
    token = float(value)
    return token / 100.0 if token > 1.0 else token


def _build_risk_limits(risk_cfg: Dict[str, Any]) -> RiskLimits:
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


def _build_broker_config(config: Dict[str, Any], *, risk_cfg: Dict[str, Any]) -> Dict[str, Any]:
    execution_cfg = config.get("execution", {})
    analytics_cfg = config.get("analytics", {})
    return {
        "enabled": True,
        "live_execution": False,
        "max_symbol_notional": risk_cfg.get("max_symbol_notional", {}),
        "max_venue_notional": risk_cfg.get("max_venue_notional", {}),
        "tca_db_path": analytics_cfg.get("tca_db_path", "data/tca_records.csv"),
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
        "capacity_curves": execution_cfg.get("capacity_curves", {}),
        "expected_alpha_bps_by_strategy": execution_cfg.get("expected_alpha_bps_by_strategy", {}),
    }


def _default_symbols(config: Dict[str, Any]) -> List[str]:
    symbols: List[str] = []
    markets = config.get("markets", {})
    for venue in markets.get("crypto", {}).get("exchanges", []):
        symbols.extend(venue.get("symbols", []))
    for venue in markets.get("equities", {}).get("brokers", []):
        symbols.extend(venue.get("symbols", []))
    for venue in markets.get("forex", {}).get("brokers", []):
        symbols.extend(venue.get("pairs", []))
    return sorted(set(str(s) for s in symbols if s))


def _write_snapshot(out_dir: Path, payload: Dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = out_dir / f"paper_campaign_snapshot_{stamp}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _current_eta_map(router: RiskAwareRouter) -> Dict[tuple[str, str], float]:
    frame = router.tca_db.as_dataframe()
    if frame.empty:
        return dict(router.eta_by_symbol_venue)

    eta_map = dict(router.eta_by_symbol_venue)
    baseline = float(router.cost_model.eta)
    unique_rows = frame[["symbol", "exchange"]].drop_duplicates()
    for _, row in unique_rows.iterrows():
        key = (str(row["symbol"]), str(row["exchange"]))
        eta_map.setdefault(key, baseline)
    return eta_map


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/paper.yaml")
    parser.add_argument(
        "--operator-tier",
        choices=["simple", "pro"],
        default="",
        help="Operator UX tier override (simple or pro).",
    )
    parser.add_argument(
        "--risk-profile",
        default="",
        help=(
            "Risk tolerance profile override "
            "(conservative, balanced, aggressive, professional, or custom key)."
        ),
    )
    parser.add_argument("--symbols", default="")
    parser.add_argument("--cycles", type=int, default=500)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--notional-usd", type=float, default=200.0)
    parser.add_argument("--readiness-every", type=int, default=50)
    parser.add_argument("--out-dir", default="data/reports")
    parser.add_argument("--max-reject-rate", type=float, default=0.4)
    parser.add_argument("--lookback-days", type=int, default=60)
    parser.add_argument("--min-days", type=int, default=30)
    parser.add_argument("--min-fills", type=int, default=200)
    parser.add_argument("--max-p95-slippage-bps", type=float, default=20.0)
    parser.add_argument("--max-mape-pct", type=float, default=35.0)
    parser.add_argument("--paper-base-slippage-bps", type=float, default=8.0)
    parser.add_argument("--paper-min-slippage-bps", type=float, default=1.0)
    parser.add_argument("--paper-stress-multiplier", type=float, default=3.0)
    parser.add_argument("--paper-stress-fill-ratio-multiplier", type=float, default=0.70)
    parser.add_argument("--max-degraded-venues", type=int, default=0)
    parser.add_argument("--max-calibration-alerts", type=int, default=0)
    parser.add_argument("--promotion-min-days", type=int, default=30)
    parser.add_argument("--promotion-max-days", type=int, default=90)
    parser.add_argument("--promotion-min-net-pnl-usd", type=float, default=0.0)
    parser.add_argument("--promotion-max-kill-switch-triggers", type=int, default=0)
    return parser


async def _run(args: argparse.Namespace) -> Dict[str, Any]:
    config = _load_yaml(args.config)
    operator_tier = resolve_operator_tier(config, override=(args.operator_tier or None))
    validate_operator_tier_overrides(
        tier=operator_tier,
        has_market_override=False,
        has_strategy_override=False,
        has_symbol_override=bool(args.symbols),
    )
    risk_cfg, risk_profile = resolve_effective_risk_config(
        config,
        override_profile=(args.risk_profile or None),
    )

    risk_limits = _build_risk_limits(risk_cfg)
    broker_config = _build_broker_config(config, risk_cfg=risk_cfg)
    fill_provider = MicrostructurePaperFillProvider(
        config=PaperFillModelConfig(
            adverse_selection_bps=float(args.paper_base_slippage_bps),
            min_slippage_bps=float(args.paper_min_slippage_bps),
            reality_stress_mode=True,
            stress_slippage_multiplier=float(args.paper_stress_multiplier),
            stress_fill_ratio_multiplier=float(args.paper_stress_fill_ratio_multiplier),
        )
    )
    router = RiskAwareRouter(
        risk_config=risk_limits,
        broker_config=broker_config,
        fill_provider=fill_provider,
    )

    if "initial_capital" not in risk_cfg:
        raise ValueError("risk.initial_capital must be set in config before paper campaign runs.")
    capital = float(risk_cfg.get("initial_capital"))
    router.set_capital(capital, source="paper_campaign")

    router.configure_market_adapters(config.get("markets", {}))
    await router.start_market_data()

    symbol_list = _parse_csv(args.symbols) if args.symbols else _default_symbols(config)
    cycle_symbols = iter_cycle_symbols(symbol_list)

    positions: Dict[str, float] = {}
    prices: Dict[str, float] = {}
    stats = CampaignStats()
    strategy_returns = {
        "campaign": np.linspace(-0.002, 0.002, 30),
    }
    revenue_diagnostics = RevenueDiagnostics(
        str(broker_config.get("tca_db_path", "data/tca_records.csv"))
    )
    campaign_expected_alpha = float(
        broker_config.get("expected_alpha_bps_by_strategy", {}).get("campaign", 0.0)
    )
    portfolio_changes = list(np.linspace(-5.0, 5.0, 30))

    out_dir = Path(args.out_dir)
    last_snapshot: Dict[str, Any] = {}

    try:
        for cycle in range(args.cycles):
            symbol = cycle_symbols[cycle % len(cycle_symbols)]
            side = "buy" if cycle % 2 == 0 else "sell"

            snapshot = await router.fetch_market_snapshot()
            selected = select_symbol_price(snapshot, symbol)
            if selected is None:
                continue

            _venue, price = selected
            prices[symbol] = float(price)
            order = build_probe_order(
                symbol=symbol,
                side=side,
                notional_usd=float(args.notional_usd),
                price=float(price),
                order_type=OrderType.LIMIT,
                strategy_id="campaign",
                expected_alpha_bps=campaign_expected_alpha,
            )

            portfolio = build_portfolio_snapshot(
                positions=positions,
                prices=prices,
                capital=capital,
            )

            result = await router.submit_order(
                order=order,
                market_data=snapshot,
                portfolio=portfolio,
                strategy_returns=strategy_returns,
                portfolio_changes=portfolio_changes,
            )

            stats.submitted += 1
            if result.success:
                stats.filled += 1
                signed_qty = order.quantity if side == "buy" else -order.quantity
                positions[symbol] = float(positions.get(symbol, 0.0)) + float(signed_qty)
            else:
                stats.rejected += 1

            if stats.reject_rate > float(args.max_reject_rate):
                break

            should_snapshot = ((cycle + 1) % max(int(args.readiness_every), 1) == 0) or (
                cycle + 1 == args.cycles
            )
            if should_snapshot:
                revenue_payload = revenue_diagnostics.payload(
                    lookback_days=int(args.lookback_days),
                    limit=20,
                )
                eta_map = _current_eta_map(router)
                updated_eta, calibration = router.run_weekly_tca_calibration(
                    eta_by_symbol_venue=eta_map,
                    min_samples=25,
                    alert_threshold_pct=float(args.max_mape_pct),
                    lookback_days=int(args.lookback_days),
                )
                readiness = router.evaluate_paper_live_readiness(
                    lookback_days=int(args.lookback_days),
                    min_days_required=int(args.min_days),
                    min_fills_required=int(args.min_fills),
                    max_p95_slippage_bps=float(args.max_p95_slippage_bps),
                    max_mape_pct=float(args.max_mape_pct),
                )
                router_stats = router.get_stats()
                reliability = router_stats.get("reliability", {})
                ops_health = evaluate_operational_health(
                    campaign_stats={
                        "submitted": stats.submitted,
                        "filled": stats.filled,
                        "rejected": stats.rejected,
                        "reject_rate": stats.reject_rate,
                    },
                    readiness=readiness,
                    reliability=reliability,
                    calibration=calibration,
                    thresholds=OpsThresholds(
                        max_reject_rate=float(args.max_reject_rate),
                        max_p95_slippage_bps=float(args.max_p95_slippage_bps),
                        max_mape_pct=float(args.max_mape_pct),
                        max_degraded_venues=int(args.max_degraded_venues),
                        max_calibration_alerts=int(args.max_calibration_alerts),
                    ),
                )
                promotion_gate = evaluate_promotion_gate(
                    readiness=readiness,
                    campaign_stats={
                        "submitted": stats.submitted,
                        "filled": stats.filled,
                        "rejected": stats.rejected,
                        "reject_rate": stats.reject_rate,
                    },
                    ops_summary=ops_health.get("summary", {}),
                    revenue_summary=(revenue_payload or {}).get("summary", {}),
                    thresholds=PromotionGateThresholds(
                        min_days=int(args.promotion_min_days),
                        max_days=int(args.promotion_max_days),
                        min_fills=int(args.min_fills),
                        max_reject_rate=float(args.max_reject_rate),
                        max_critical_alerts=0,
                        min_net_pnl_after_costs_usd=float(args.promotion_min_net_pnl_usd),
                        max_slippage_mape_pct=float(args.max_mape_pct),
                        max_kill_switch_triggers=int(args.promotion_max_kill_switch_triggers),
                    ),
                )
                last_snapshot = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "risk_profile": risk_profile_payload(risk_profile),
                    "operator_tier": operator_tier.name,
                    "cycle": cycle + 1,
                    "stats": {
                        "submitted": stats.submitted,
                        "filled": stats.filled,
                        "rejected": stats.rejected,
                        "reject_rate": stats.reject_rate,
                    },
                    "eta": {
                        "markets": {
                            f"{key[0]}@{key[1]}": float(val) for key, val in updated_eta.items()
                        },
                    },
                    "reliability": reliability,
                    "calibration": calibration,
                    "readiness": readiness,
                    "ops_health": ops_health,
                    "promotion_gate": promotion_gate,
                    "revenue": revenue_payload,
                }
                path = _write_snapshot(out_dir, last_snapshot)
                print(
                    "snapshot="
                    f"{path} readiness={readiness['ready_for_canary']} "
                    f"promotion={promotion_gate['decision']}"
                )

            if float(args.sleep_seconds) > 0:
                await asyncio.sleep(float(args.sleep_seconds))

    finally:
        await router.stop_market_data()

    final = {
        "risk_profile": risk_profile_payload(risk_profile),
        "operator_tier": operator_tier.name,
        "submitted": stats.submitted,
        "filled": stats.filled,
        "rejected": stats.rejected,
        "reject_rate": stats.reject_rate,
        "ops_health": last_snapshot.get("ops_health", {}),
        "promotion_gate": last_snapshot.get("promotion_gate", {}),
        "reliability": last_snapshot.get("reliability", {}),
        "readiness": last_snapshot.get("readiness", {}),
        "revenue": last_snapshot.get("revenue", {}),
    }
    return final


def main() -> int:
    args = build_arg_parser().parse_args()
    final = asyncio.run(_run(args))
    print(json.dumps(final, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
