"""Promotion-gate evaluation for 30-90 day paper campaigns."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class PromotionGateThresholds:
    """Thresholds for paper-to-canary promotion decisions."""

    min_days: int = 30
    max_days: int = 90
    min_fills: int = 200
    max_reject_rate: float = 0.40
    max_critical_alerts: int = 0
    min_net_pnl_after_costs_usd: float = 0.0
    max_slippage_mape_pct: float = 35.0
    max_kill_switch_triggers: int = 0


def evaluate_promotion_gate(
    *,
    readiness: Dict[str, Any],
    campaign_stats: Dict[str, Any],
    ops_summary: Dict[str, Any],
    revenue_summary: Dict[str, Any] | None = None,
    thresholds: PromotionGateThresholds | None = None,
) -> Dict[str, Any]:
    """Evaluate deterministic promotion decision from campaign/readiness/ops data."""
    gate = thresholds or PromotionGateThresholds()

    trading_days = int(readiness.get("trading_days", 0))
    fills = int(readiness.get("fills", 0))
    ready_for_canary = bool(readiness.get("ready_for_canary", False))
    reject_rate = float(campaign_stats.get("reject_rate", 0.0))
    critical_alerts = int(ops_summary.get("critical", 0))
    net_pnl_after_costs = float(
        (revenue_summary or {}).get("estimated_realized_pnl_usd", readiness.get("total_pnl", 0.0))
    )
    slippage_mape_pct = float(readiness.get("slippage_mape_pct", 0.0))
    kill_switch_triggers = int(readiness.get("kill_switch_triggers", 0))

    checks = {
        "min_days": trading_days >= int(gate.min_days),
        "max_days_window": trading_days <= int(gate.max_days),
        "min_fills": fills >= int(gate.min_fills),
        "ready_for_canary": ready_for_canary,
        "reject_rate": reject_rate <= float(gate.max_reject_rate),
        "critical_alerts": critical_alerts <= int(gate.max_critical_alerts),
        "net_pnl_after_costs": net_pnl_after_costs >= float(gate.min_net_pnl_after_costs_usd),
        "slippage_mape_pct": slippage_mape_pct <= float(gate.max_slippage_mape_pct),
        "kill_switch_triggers": kill_switch_triggers <= int(gate.max_kill_switch_triggers),
    }

    if checks["ready_for_canary"] and all(
        checks[k]
        for k in (
            "min_days",
            "max_days_window",
            "min_fills",
            "reject_rate",
            "critical_alerts",
            "net_pnl_after_costs",
            "slippage_mape_pct",
            "kill_switch_triggers",
        )
    ):
        decision = "promote_to_live_canary"
    elif trading_days > int(gate.max_days) and not checks["ready_for_canary"]:
        decision = "reject_or_research"
    else:
        decision = "remain_in_paper"

    return {
        "decision": decision,
        "checks": checks,
        "metrics": {
            "trading_days": trading_days,
            "fills": fills,
            "reject_rate": reject_rate,
            "critical_alerts": critical_alerts,
            "net_pnl_after_costs_usd": net_pnl_after_costs,
            "slippage_mape_pct": slippage_mape_pct,
            "kill_switch_triggers": kill_switch_triggers,
        },
        "thresholds": asdict(gate),
    }
