"""Wedge-first market scope governance contracts (COMP-10)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class ScopeReadinessGates:
    min_execution_quality: float = 0.70
    min_reconciliation_accuracy: float = 0.97
    max_open_p1_incidents: int = 0


@dataclass(frozen=True)
class MarketScopePolicy:
    primary_wedge_market: str
    max_additional_markets_per_phase: int
    readiness_gates: ScopeReadinessGates


def resolve_market_scope_policy(config: Mapping[str, Any]) -> MarketScopePolicy:
    runtime = config.get("runtime", {}) if isinstance(config, Mapping) else {}
    policy = runtime.get("market_scope_policy", {}) if isinstance(runtime, Mapping) else {}
    if not isinstance(policy, Mapping):
        policy = {}

    gate_cfg = policy.get("readiness_gates", {})
    if not isinstance(gate_cfg, Mapping):
        gate_cfg = {}

    primary = str(policy.get("primary_wedge_market", "crypto")).strip().lower() or "crypto"
    max_expand = max(int(policy.get("max_additional_markets_per_phase", 1)), 0)
    gates = ScopeReadinessGates(
        min_execution_quality=float(gate_cfg.get("min_execution_quality", 0.70)),
        min_reconciliation_accuracy=float(gate_cfg.get("min_reconciliation_accuracy", 0.97)),
        max_open_p1_incidents=max(int(gate_cfg.get("max_open_p1_incidents", 0)), 0),
    )
    return MarketScopePolicy(
        primary_wedge_market=primary,
        max_additional_markets_per_phase=max_expand,
        readiness_gates=gates,
    )


def evaluate_market_scope_request(
    *,
    policy: MarketScopePolicy,
    requested_markets: Iterable[str],
    readiness: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = [str(item).strip().lower() for item in requested_markets if str(item).strip()]
    deduped = list(dict.fromkeys(normalized))
    if not deduped:
        deduped = [policy.primary_wedge_market]

    readiness_payload = dict(readiness or {})
    execution_quality = float(readiness_payload.get("execution_quality", 1.0))
    reconciliation_accuracy = float(readiness_payload.get("reconciliation_accuracy", 1.0))
    open_p1_incidents = int(readiness_payload.get("open_p1_incidents", 0))

    expansion = [m for m in deduped if m != policy.primary_wedge_market]
    reasons: list[str] = []

    if len(expansion) > int(policy.max_additional_markets_per_phase):
        reasons.append("too_many_markets_for_one_phase")

    gates_passed = (
        execution_quality >= float(policy.readiness_gates.min_execution_quality)
        and reconciliation_accuracy >= float(policy.readiness_gates.min_reconciliation_accuracy)
        and open_p1_incidents <= int(policy.readiness_gates.max_open_p1_incidents)
    )
    if expansion and not gates_passed:
        reasons.append("readiness_gates_failed")

    approved = list(deduped)

    return {
        "passed": not reasons,
        "requested_markets": deduped,
        "approved_markets": approved,
        "primary_wedge_market": policy.primary_wedge_market,
        "expansion_count": len(expansion),
        "max_additional_markets_per_phase": int(policy.max_additional_markets_per_phase),
        "gates": {
            "execution_quality": execution_quality,
            "reconciliation_accuracy": reconciliation_accuracy,
            "open_p1_incidents": open_p1_incidents,
            "min_execution_quality": float(policy.readiness_gates.min_execution_quality),
            "min_reconciliation_accuracy": float(policy.readiness_gates.min_reconciliation_accuracy),
            "max_open_p1_incidents": int(policy.readiness_gates.max_open_p1_incidents),
        },
        "reasons": reasons,
    }
