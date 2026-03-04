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
    min_purged_cv_sharpe: float = 1.0
    min_walk_forward_sharpe: float = 1.0
    min_deflated_sharpe: float = 0.8
    require_purged_cv_passed: bool = True
    require_walk_forward_passed: bool = True
    require_deflated_sharpe_passed: bool = True


def evaluate_promotion_gate(
    *,
    readiness: Dict[str, Any],
    campaign_stats: Dict[str, Any],
    ops_summary: Dict[str, Any],
    research_validation: Dict[str, Any] | None = None,
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
    validation = dict(research_validation or {})

    purged_cv_sharpe = float(validation.get("purged_cv_sharpe", 0.0))
    walk_forward_sharpe = float(validation.get("walk_forward_sharpe", 0.0))
    deflated_sharpe = float(validation.get("deflated_sharpe", 0.0))
    purged_cv_passed = bool(
        validation.get("purged_cv_passed", purged_cv_sharpe >= float(gate.min_purged_cv_sharpe))
    )
    walk_forward_passed = bool(
        validation.get(
            "walk_forward_passed",
            walk_forward_sharpe >= float(gate.min_walk_forward_sharpe),
        )
    )
    deflated_sharpe_passed = bool(
        validation.get(
            "deflated_sharpe_passed",
            deflated_sharpe >= float(gate.min_deflated_sharpe),
        )
    )
    paper_track_record_passed = bool(readiness.get("ready_for_canary", False))

    checks = {
        "min_days": trading_days >= int(gate.min_days),
        "max_days_window": trading_days <= int(gate.max_days),
        "min_fills": fills >= int(gate.min_fills),
        "paper_track_record": paper_track_record_passed and ready_for_canary,
        "reject_rate": reject_rate <= float(gate.max_reject_rate),
        "critical_alerts": critical_alerts <= int(gate.max_critical_alerts),
        "net_pnl_after_costs": net_pnl_after_costs >= float(gate.min_net_pnl_after_costs_usd),
        "slippage_mape_pct": slippage_mape_pct <= float(gate.max_slippage_mape_pct),
        "kill_switch_triggers": kill_switch_triggers <= int(gate.max_kill_switch_triggers),
        "purged_cv_sharpe": purged_cv_sharpe >= float(gate.min_purged_cv_sharpe),
        "walk_forward_sharpe": walk_forward_sharpe >= float(gate.min_walk_forward_sharpe),
        "deflated_sharpe": deflated_sharpe >= float(gate.min_deflated_sharpe),
        "purged_cv_passed": purged_cv_passed if bool(gate.require_purged_cv_passed) else True,
        "walk_forward_passed": (
            walk_forward_passed if bool(gate.require_walk_forward_passed) else True
        ),
        "deflated_sharpe_passed": (
            deflated_sharpe_passed if bool(gate.require_deflated_sharpe_passed) else True
        ),
    }

    if checks["paper_track_record"] and all(
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
            "purged_cv_sharpe",
            "walk_forward_sharpe",
            "deflated_sharpe",
            "purged_cv_passed",
            "walk_forward_passed",
            "deflated_sharpe_passed",
        )
    ):
        decision = "promote_to_live_canary"
    elif trading_days > int(gate.max_days) and not checks["paper_track_record"]:
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
            "purged_cv_sharpe": purged_cv_sharpe,
            "walk_forward_sharpe": walk_forward_sharpe,
            "deflated_sharpe": deflated_sharpe,
            "purged_cv_passed": purged_cv_passed,
            "walk_forward_passed": walk_forward_passed,
            "deflated_sharpe_passed": deflated_sharpe_passed,
        },
        "thresholds": asdict(gate),
    }
