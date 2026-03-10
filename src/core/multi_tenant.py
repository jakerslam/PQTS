"""Tenant entitlements for operator UX + strategy access controls."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TIER_POLICY_PATH = REPO_ROOT / "config" / "entitlements" / "tier_policy.json"


@dataclass(frozen=True)
class TenantEntitlements:
    tenant_id: str
    plan: str
    allowed_markets: Optional[Set[str]]
    strategy_allowlist: Optional[Set[str]]
    min_active_strategies: int
    max_active_strategies: int
    allow_live_trading: bool
    requires_paper_readiness_for_live: bool = False
    requires_operator_ack_for_live: bool = False


@dataclass(frozen=True)
class TenantEnforcementResult:
    selected: List[str]
    active_markets: List[str]
    dropped_markets: List[str]
    dropped_strategies: List[str]
    reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected": list(self.selected),
            "active_markets": list(self.active_markets),
            "dropped_markets": list(self.dropped_markets),
            "dropped_strategies": list(self.dropped_strategies),
            "reasons": list(self.reasons),
        }


def _as_set(values: Any) -> Optional[Set[str]]:
    if values is None:
        return None
    if isinstance(values, str):
        token = values.strip()
        return {token} if token else set()
    out: Set[str] = set()
    for value in values:
        token = str(value).strip()
        if token:
            out.add(token)
    return out


def _build_tenant_entitlement(*, plan: str, row: Mapping[str, Any]) -> TenantEntitlements:
    return TenantEntitlements(
        tenant_id=str(row.get("tenant_id", plan)).strip() or plan,
        plan=str(plan).strip().lower(),
        allowed_markets=_as_set(row.get("allowed_markets")),
        strategy_allowlist=_as_set(row.get("strategy_allowlist")),
        min_active_strategies=max(int(row.get("min_active_strategies", 1)), 1),
        max_active_strategies=max(
            int(row.get("max_active_strategies", 1)),
            max(int(row.get("min_active_strategies", 1)), 1),
        ),
        allow_live_trading=bool(row.get("allow_live_trading", False)),
        requires_paper_readiness_for_live=bool(row.get("requires_paper_readiness_for_live", False)),
        requires_operator_ack_for_live=bool(row.get("requires_operator_ack_for_live", False)),
    )


def _default_plans() -> Dict[str, TenantEntitlements]:
    payload = {
        "community": {
            "allowed_markets": {"crypto"},
            "strategy_allowlist": {"trend_following", "mean_reversion", "swing_trend", "hold_carry"},
            "min_active_strategies": 1,
            "max_active_strategies": 3,
            "allow_live_trading": False,
            "requires_paper_readiness_for_live": False,
            "requires_operator_ack_for_live": False,
        },
        "solo_pro": {
            "allowed_markets": {"crypto", "equities", "forex"},
            "strategy_allowlist": None,
            "min_active_strategies": 1,
            "max_active_strategies": 8,
            "allow_live_trading": True,
            "requires_paper_readiness_for_live": True,
            "requires_operator_ack_for_live": True,
        },
        "team": {
            "allowed_markets": {"crypto", "equities", "forex"},
            "strategy_allowlist": None,
            "min_active_strategies": 1,
            "max_active_strategies": 24,
            "allow_live_trading": True,
            "requires_paper_readiness_for_live": True,
            "requires_operator_ack_for_live": True,
        },
        "enterprise": {
            "allowed_markets": None,
            "strategy_allowlist": None,
            "min_active_strategies": 1,
            "max_active_strategies": 64,
            "allow_live_trading": True,
            "requires_paper_readiness_for_live": True,
            "requires_operator_ack_for_live": True,
        },
    }
    return {key: _build_tenant_entitlement(plan=key, row=value) for key, value in payload.items()}


def _load_policy_plans(config: Mapping[str, Any]) -> tuple[Dict[str, TenantEntitlements], Dict[str, str], str]:
    runtime = config.get("runtime", {}) if isinstance(config, Mapping) else {}
    tenant_cfg = runtime.get("tenant", {}) if isinstance(runtime, Mapping) else {}
    if not isinstance(tenant_cfg, Mapping):
        tenant_cfg = {}

    policy_path_raw = str(tenant_cfg.get("tier_policy_path", "")).strip()
    policy_path = Path(policy_path_raw) if policy_path_raw else DEFAULT_TIER_POLICY_PATH

    if not policy_path.exists():
        defaults = _default_plans()
        aliases = {
            "starter": "community",
            "pro": "solo_pro",
            "professional": "solo_pro",
        }
        return defaults, aliases, "enterprise"

    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    plans_payload = payload.get("plans", {})
    if not isinstance(plans_payload, Mapping) or not plans_payload:
        raise ValueError(f"tier policy has no plans: {policy_path}")

    plans: Dict[str, TenantEntitlements] = {}
    for key, row in plans_payload.items():
        if not isinstance(row, Mapping):
            continue
        token = str(key).strip().lower()
        if not token:
            continue
        plans[token] = _build_tenant_entitlement(plan=token, row=row)

    if not plans:
        raise ValueError(f"tier policy has no valid plan rows: {policy_path}")

    alias_payload = payload.get("aliases", {})
    aliases: Dict[str, str] = {}
    if isinstance(alias_payload, Mapping):
        for key, value in alias_payload.items():
            k = str(key).strip().lower()
            v = str(value).strip().lower()
            if k and v:
                aliases[k] = v

    default_plan = str(payload.get("default_plan", "enterprise")).strip().lower() or "enterprise"
    return plans, aliases, default_plan


def resolve_tenant_entitlements(
    config: Mapping[str, Any],
    *,
    tenant_id_override: Optional[str] = None,
    plan_override: Optional[str] = None,
) -> TenantEntitlements:
    runtime = config.get("runtime", {})
    tenant_cfg: Mapping[str, Any] = {}
    if isinstance(runtime, Mapping):
        raw = runtime.get("tenant", {}) or {}
        if isinstance(raw, Mapping):
            tenant_cfg = raw

    plans, aliases, default_plan = _load_policy_plans(config)

    raw_plan = (
        str(
            plan_override
            or tenant_cfg.get("plan", "")
            or (runtime.get("tenant_plan", "") if isinstance(runtime, Mapping) else "")
            or default_plan
        )
        .strip()
        .lower()
    )
    plan = aliases.get(raw_plan, raw_plan)
    if plan not in plans:
        supported = ", ".join(sorted(plans.keys()))
        raise ValueError(f"Unknown tenant plan '{raw_plan}'. Supported: {supported}")
    base = plans[plan]

    tenant_id = str(tenant_id_override or tenant_cfg.get("tenant_id", "default")).strip() or "default"
    allowed_markets = _as_set(tenant_cfg.get("allowed_markets", base.allowed_markets))
    strategy_allowlist = _as_set(tenant_cfg.get("strategy_allowlist", base.strategy_allowlist))
    min_active = max(int(tenant_cfg.get("min_active_strategies", base.min_active_strategies)), 1)
    max_active = max(
        int(tenant_cfg.get("max_active_strategies", base.max_active_strategies)), min_active
    )
    allow_live = bool(tenant_cfg.get("allow_live_trading", base.allow_live_trading))
    require_paper = bool(
        tenant_cfg.get(
            "requires_paper_readiness_for_live",
            base.requires_paper_readiness_for_live,
        )
    )
    require_ack = bool(
        tenant_cfg.get(
            "requires_operator_ack_for_live",
            base.requires_operator_ack_for_live,
        )
    )

    return TenantEntitlements(
        tenant_id=tenant_id,
        plan=plan,
        allowed_markets=allowed_markets,
        strategy_allowlist=strategy_allowlist,
        min_active_strategies=min_active,
        max_active_strategies=max_active,
        allow_live_trading=allow_live,
        requires_paper_readiness_for_live=require_paper,
        requires_operator_ack_for_live=require_ack,
    )


def enforce_live_enablement_preconditions(
    *,
    entitlements: TenantEntitlements,
    runtime: Mapping[str, Any],
) -> dict[str, Any]:
    live_readiness = runtime.get("live_readiness", {}) if isinstance(runtime, Mapping) else {}
    if not isinstance(live_readiness, Mapping):
        live_readiness = {}

    paper_ready = bool(live_readiness.get("paper_ready", False))
    operator_ack = bool(live_readiness.get("operator_acknowledged", False))
    reasons: list[str] = []

    if entitlements.requires_paper_readiness_for_live and not paper_ready:
        reasons.append("paper_readiness_required")
    if entitlements.requires_operator_ack_for_live and not operator_ack:
        reasons.append("operator_ack_required")

    return {
        "passed": not reasons,
        "paper_ready": paper_ready,
        "operator_acknowledged": operator_ack,
        "reasons": reasons,
    }


def enforce_tenant_entitlements(
    *,
    selected: Iterable[str],
    active_markets: Iterable[str],
    ranked_candidates: Iterable[str],
    entitlements: TenantEntitlements,
) -> TenantEnforcementResult:
    selected_list = [str(name) for name in selected if str(name).strip()]
    markets = [str(name) for name in active_markets if str(name).strip()]
    ranked = [str(name) for name in ranked_candidates if str(name).strip()]

    dropped_markets: List[str] = []
    dropped_strategies: List[str] = []
    reasons: List[str] = []

    if entitlements.allowed_markets is not None:
        allowed_markets = set(entitlements.allowed_markets)
        filtered_markets = [market for market in markets if market in allowed_markets]
        dropped_markets = sorted(set(markets).difference(filtered_markets))
        if dropped_markets:
            reasons.append("dropped_markets_not_permitted_by_plan")
        if not filtered_markets and allowed_markets:
            filtered_markets = sorted(allowed_markets)[:1]
            reasons.append("fallback_market_selected_from_allowed_set")
        markets = filtered_markets

    if entitlements.strategy_allowlist is not None:
        allowed_strategies = set(entitlements.strategy_allowlist)
        filtered = [name for name in selected_list if name in allowed_strategies]
        dropped_strategies.extend(sorted(set(selected_list).difference(filtered)))
        if len(filtered) != len(selected_list):
            reasons.append("dropped_strategies_not_permitted_by_plan")
        selected_list = filtered

    seen = set()
    deduped: List[str] = []
    for name in selected_list:
        if name in seen:
            continue
        seen.add(name)
        deduped.append(name)
    selected_list = deduped

    if len(selected_list) > entitlements.max_active_strategies:
        dropped_strategies.extend(selected_list[entitlements.max_active_strategies :])
        selected_list = selected_list[: entitlements.max_active_strategies]
        reasons.append("trimmed_to_plan_max_active_strategies")

    if len(selected_list) < entitlements.min_active_strategies:
        allowlist = (
            set(entitlements.strategy_allowlist)
            if entitlements.strategy_allowlist is not None
            else None
        )
        for candidate in ranked:
            if candidate in selected_list:
                continue
            if allowlist is not None and candidate not in allowlist:
                continue
            selected_list.append(candidate)
            if len(selected_list) >= entitlements.min_active_strategies:
                reasons.append("expanded_to_plan_min_active_strategies")
                break

    return TenantEnforcementResult(
        selected=list(selected_list),
        active_markets=list(markets),
        dropped_markets=sorted(set(dropped_markets)),
        dropped_strategies=sorted(set(dropped_strategies)),
        reasons=list(reasons),
    )
