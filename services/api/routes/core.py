"""Core REST endpoints for account, portfolio, execution, PnL, and risk resources."""

from __future__ import annotations

import hashlib
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Annotated, Any
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from contracts.api import (
    AccountSummary,
    FillSnapshot,
    OrderSnapshot,
    PnLSnapshot,
    PositionSnapshot,
    RiskStateSnapshot,
)
from services.api.auth import APIIdentity, require_identity, require_operator
from services.api.cache import APICache, enforce_rate_limit, get_cache
from services.api.correlation import read_request_correlation, with_correlation
from services.api.ops_data import (
    build_data_seed_command,
    build_notify_command,
    build_order_truth,
    data_seed_presets,
    list_template_run_artifacts,
    load_reference_performance,
    load_reference_provenance,
    parse_last_json_line,
    run_python_command,
    summarize_execution_quality,
    summarize_replay,
)
from services.api.persistence import APIPersistence, get_persistence
from services.api.state import APIRuntimeStore, StreamHub, get_store, get_stream_hub

router = APIRouter(prefix="/v1", tags=["core"])


def _invalid_payload(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid payload: {exc}",
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_PROMOTION_STAGE_ORDER = ("backtest", "paper", "shadow", "canary", "live")
_ONBOARDING_EXPERIENCE = {"beginner", "intermediate", "advanced"}
_ONBOARDING_AUTOMATION = {"manual", "assisted", "auto"}
_BROKERAGE_STALE_AFTER_SECONDS = 300
_CAPITAL_ACTION_TOKENS = ("trade", "order", "buy", "sell", "rebalance", "execute")
_AGENT_ACTIONS = {
    "promote_to_paper",
    "promote_to_live_canary",
    "promote_to_live",
    "hold",
    "demote",
    "kill",
}
_AGENT_REQUIRED_FIELDS = (
    "action",
    "strategy_id",
    "rationale",
    "supporting_card_ids",
    "current_metrics",
    "gate_checks",
    "risk_impact",
)
_AGENT_HOOK_EVENTS = {"intent_status", "promotion_update", "risk_incident", "sync_health"}
_AGENT_HOOK_ALLOWED_HOSTS = (
    "localhost",
    "127.0.0.1",
    "hooks.slack.com",
    "slack.com",
    "discord.com",
    "discordapp.com",
    "api.telegram.org",
    "webhook.site",
)


def _default_promotion_record(strategy_id: str) -> dict[str, Any]:
    return {
        "strategy_id": strategy_id,
        "stage": "paper",
        "capital_allocation_pct": 2.0,
        "rollback_trigger": "reject_rate>0.30 or slippage_mape_pct>25",
        "updated_at": _utc_now_iso(),
        "history": [],
    }


def _fingerprint_secret(token: str) -> str:
    normalized = token.strip()
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _build_demo_brokerage_accounts(*, connection_id: str, institution: str) -> list[dict[str, Any]]:
    seed = int(hashlib.sha256(connection_id.encode("utf-8")).hexdigest()[:8], 16)
    cash = 12_000.0 + float(seed % 3500)
    margin = 8_500.0 + float(seed % 2200)
    return [
        {
            "account_id": f"{connection_id}_cash",
            "connection_id": connection_id,
            "provider": "plaid",
            "institution": institution,
            "name": "Brokerage Cash",
            "type": "brokerage",
            "subtype": "cash",
            "currency": "USD",
            "balance_current": round(cash, 2),
            "balance_available": round(cash, 2),
            "as_of": _utc_now_iso(),
        },
        {
            "account_id": f"{connection_id}_margin",
            "connection_id": connection_id,
            "provider": "plaid",
            "institution": institution,
            "name": "Brokerage Margin",
            "type": "brokerage",
            "subtype": "margin",
            "currency": "USD",
            "balance_current": round(margin, 2),
            "balance_available": round(max(margin - 500.0, 0.0), 2),
            "as_of": _utc_now_iso(),
        },
    ]


def _portfolio_totals(accounts: list[dict[str, Any]]) -> dict[str, float]:
    current = 0.0
    available = 0.0
    for row in accounts:
        try:
            current += float(row.get("balance_current", 0.0) or 0.0)
        except (TypeError, ValueError):
            pass
        try:
            available += float(row.get("balance_available", 0.0) or 0.0)
        except (TypeError, ValueError):
            pass
    return {
        "accounts": float(len(accounts)),
        "total_balance_current_usd": round(current, 2),
        "total_balance_available_usd": round(available, 2),
    }


def _compute_sync_state(link: dict[str, Any]) -> dict[str, Any]:
    last_sync = str(link.get("last_sync_at", "")).strip()
    stale_after = int(link.get("stale_after_seconds", _BROKERAGE_STALE_AFTER_SECONDS))
    is_stale = True
    stale_seconds: int | None = None
    if last_sync:
        try:
            synced_at = datetime.fromisoformat(last_sync)
            stale_seconds = max(int((datetime.now(timezone.utc) - synced_at).total_seconds()), 0)
            is_stale = stale_seconds > stale_after
        except ValueError:
            is_stale = True
    status = "ok"
    if bool(link.get("status", "") == "revoked"):
        status = "down"
    elif is_stale:
        status = "stale"
    return {
        "status": status,
        "is_stale": is_stale,
        "stale_seconds": stale_seconds,
        "stale_after_seconds": stale_after,
        "fail_closed_trade_block": is_stale or status == "down",
    }


def _collect_brokerage_accounts(store: APIRuntimeStore) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for accounts in store.brokerage_accounts.values():
        for row in accounts:
            if isinstance(row, dict):
                rows.append(dict(row))
    rows.sort(key=lambda item: str(item.get("account_id", "")))
    return rows


def _collect_brokerage_sync_health(store: APIRuntimeStore) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for link in store.brokerage_links.values():
        if not isinstance(link, dict):
            continue
        state = _compute_sync_state(link)
        rows.append({
            "link_id": str(link.get("link_id", "")),
            "connection_id": str(link.get("connection_id", "")),
            "provider": str(link.get("provider", "plaid")),
            "institution": str(link.get("institution", "")),
            "last_sync_at": str(link.get("last_sync_at", "")),
            **state,
        })
    rows.sort(key=lambda item: str(item.get("link_id", "")))
    return rows


def _default_agent_policy(agent_id: str) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "capabilities": {
            "read": True,
            "propose": True,
            "simulate": True,
            "execute": False,
            "hooks_manage": True,
        },
        "max_pending_intents": 20,
        "risk_budget_pct": 2.0,
        "allowed_markets": ["crypto"],
        "allowed_actions": sorted(_AGENT_ACTIONS),
        "updated_at": _utc_now_iso(),
    }


def _get_agent_policy(store: APIRuntimeStore, agent_id: str) -> dict[str, Any]:
    existing = store.agent_policies.get(agent_id)
    if isinstance(existing, dict):
        return existing
    created = _default_agent_policy(agent_id)
    store.agent_policies[agent_id] = created
    return created


def _count_pending_intents(store: APIRuntimeStore, agent_id: str) -> int:
    count = 0
    for intent in store.agent_intents.values():
        if not isinstance(intent, dict):
            continue
        if str(intent.get("agent_id", "")) != agent_id:
            continue
        if str(intent.get("status", "")) in {"proposed", "simulated"}:
            count += 1
    return count


def _ensure_agent_capability(policy: dict[str, Any], capability: str) -> None:
    capabilities = policy.get("capabilities", {})
    enabled = False
    if isinstance(capabilities, dict):
        enabled = bool(capabilities.get(capability, False))
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Agent capability denied: {capability}",
        )


def _validate_agent_intent_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in _AGENT_REQUIRED_FIELDS:
        if key not in payload:
            errors.append(f"missing required field: {key}")
    action = str(payload.get("action", "")).strip().lower()
    if action not in _AGENT_ACTIONS:
        errors.append(f"unsupported action: {action}")
    strategy_id = str(payload.get("strategy_id", "")).strip()
    if not strategy_id:
        errors.append("strategy_id must be non-empty")
    supporting = payload.get("supporting_card_ids", [])
    if not isinstance(supporting, list) or not supporting:
        errors.append("supporting_card_ids must be a non-empty array")
    if not isinstance(payload.get("current_metrics", {}), dict):
        errors.append("current_metrics must be an object")
    if not isinstance(payload.get("gate_checks", {}), dict):
        errors.append("gate_checks must be an object")
    if not isinstance(payload.get("risk_impact", {}), dict):
        errors.append("risk_impact must be an object")
    return errors


def _proposed_stage_for_action(*, action: str, current_stage: str) -> str:
    if action == "hold":
        return current_stage
    if action == "kill":
        return "halted"
    if action == "demote":
        return _next_stage(current_stage, "rollback")
    if action == "promote_to_paper":
        return "paper"
    if action == "promote_to_live_canary":
        return "canary"
    if action == "promote_to_live":
        return "live"
    return current_stage


def _is_live_promotion(action: str) -> bool:
    return action in {"promote_to_live_canary", "promote_to_live"}


def _evaluate_stage_gate(*, action: str, current_stage: str, target_stage: str) -> tuple[bool, str]:
    stage = _coerce_stage(current_stage)
    if action == "promote_to_paper":
        if stage in {"backtest", "paper"}:
            return True, "ok"
        return False, f"invalid promote_to_paper transition from {stage}"
    if action == "promote_to_live_canary":
        if stage in {"paper", "shadow", "canary"}:
            return True, "ok"
        return False, f"invalid promote_to_live_canary transition from {stage}"
    if action == "promote_to_live":
        if stage in {"canary", "live"}:
            return True, "ok"
        return False, f"invalid promote_to_live transition from {stage}"
    if action == "demote":
        if stage in {"backtest"}:
            return False, "cannot demote below backtest"
        return True, "ok"
    if action in {"hold", "kill"}:
        return True, "ok"
    return False, f"unsupported action: {action}"


def _build_agent_gate_checks(intent: dict[str, Any], store: APIRuntimeStore) -> dict[str, Any]:
    strategy_id = str(intent.get("strategy_id", "")).strip()
    action = str(intent.get("action", "")).strip().lower()
    promotion = store.promotion_records.get(strategy_id) or _default_promotion_record(strategy_id)
    current_stage = _coerce_stage(str(promotion.get("stage", "paper")))
    target_stage = _proposed_stage_for_action(action=action, current_stage=current_stage)
    stage_ok, stage_reason = _evaluate_stage_gate(action=action, current_stage=current_stage, target_stage=target_stage)

    risk = store.risk_states.get("paper-main")
    kill_switch_active = bool(getattr(risk, "kill_switch_active", False)) if risk is not None else False
    sync_rows = _collect_brokerage_sync_health(store)
    degraded = [row for row in sync_rows if bool(row.get("fail_closed_trade_block"))]
    has_links = len(sync_rows) > 0

    checks = {
        "stage_gate_passed": stage_ok,
        "stage_gate_reason": stage_reason,
        "target_stage": target_stage,
        "kill_switch_clear": not kill_switch_active,
        "sync_health_clear": len(degraded) == 0,
        "has_brokerage_links": has_links,
    }
    reasons: list[str] = []
    if not stage_ok:
        reasons.append(stage_reason)
    if _is_live_promotion(action) and kill_switch_active:
        reasons.append("kill_switch_active")
    if _is_live_promotion(action) and not has_links:
        reasons.append("missing_brokerage_link")
    if _is_live_promotion(action) and degraded:
        reasons.append("sync_fail_closed")
    checks["blocked_reasons"] = reasons
    checks["passed"] = len(reasons) == 0
    return checks


def _record_agent_receipt(
    store: APIRuntimeStore,
    *,
    receipt_type: str,
    intent_id: str,
    agent_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    receipt = {
        "receipt_id": f"rcpt_{uuid4().hex[:10]}",
        "type": receipt_type,
        "intent_id": intent_id,
        "agent_id": agent_id,
        "timestamp": _utc_now_iso(),
        "payload": payload,
    }
    store.agent_receipts[receipt["receipt_id"]] = receipt
    return receipt


def _normalize_hook_url(raw: str) -> tuple[str, str]:
    parsed = urlparse(raw.strip())
    if parsed.scheme not in {"https", "http"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="hook URL must be http(s)")
    host = str(parsed.hostname or "").strip().lower()
    if not host:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="hook URL missing host")
    if parsed.scheme == "http" and host not in {"localhost", "127.0.0.1"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="http hooks are limited to localhost")
    if not any(host == allowed or host.endswith(f".{allowed}") for allowed in _AGENT_HOOK_ALLOWED_HOSTS):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="hook host not allowlisted")
    return parsed.geturl(), host


def _identity_is_operator(identity: APIIdentity) -> bool:
    return identity.role.value in {"operator", "admin"}


def _assert_agent_access(identity: APIIdentity, agent_id: str) -> None:
    if identity.subject == agent_id or _identity_is_operator(identity):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="agent scope denied")


def _normalize_experience(value: Any) -> str:
    token = str(value or "beginner").strip().lower()
    return token if token in _ONBOARDING_EXPERIENCE else "beginner"


def _normalize_automation(value: Any) -> str:
    token = str(value or "manual").strip().lower()
    return token if token in _ONBOARDING_AUTOMATION else "manual"


def _normalize_capital(value: Any) -> int:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return 5000
    return max(100, parsed)


def _infer_risk_profile(*, experience: str, automation: str, capital_usd: int) -> str:
    if experience == "advanced" and automation == "auto" and capital_usd >= 25000:
        return "aggressive"
    if experience == "beginner":
        return "conservative"
    return "balanced"


def _build_onboarding_plan(*, experience: str, automation: str, capital_usd: int) -> dict[str, Any]:
    risk_profile = _infer_risk_profile(
        experience=experience,
        automation=automation,
        capital_usd=capital_usd,
    )
    commands = [
        "pqts doctor --fix",
        "pqts quickstart --execute",
        f"pqts risk recommend --experience {experience} --capital-usd {capital_usd} --automation {automation}",
        f"pqts paper start --risk-profile {risk_profile}",
        "pqts status readiness",
        "pqts status leaderboard",
    ]
    return {
        "riskProfile": risk_profile,
        "commands": commands,
        "notes": [
            "UI-generated actions remain code-visible and traceable.",
            "Default flow is paper-first and cannot trigger live execution.",
        ],
        "generatedConfig": {
            "experience": experience,
            "automation": automation,
            "capital_usd": capital_usd,
            "risk_profile": risk_profile,
            "paper_first": True,
            "allow_live": False,
        },
        "uiToCliDiff": [
            f"risk_profile: {risk_profile}",
            f"capital_usd: {capital_usd}",
            f"automation: {automation}",
        ],
    }


def _build_onboarding_run(*, run_id: str, commands: list[str]) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "created_at": _utc_now_iso(),
        "status": "queued",
        "steps": [
            {
                "id": f"step_{idx + 1}",
                "label": " ".join(command.split(" ")[:2]),
                "command": command,
                "status": "pending",
            }
            for idx, command in enumerate(commands)
        ],
        "artifacts": [],
    }


def _simulate_onboarding_progress(store: APIRuntimeStore, run_id: str) -> None:
    run = store.onboarding_runs.get(run_id)
    if run is None:
        return
    run["status"] = "running"
    run["started_at"] = _utc_now_iso()
    report_root = f"data/reports/quickstart/{run_id}"
    steps = run.get("steps", [])
    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        step["status"] = "running"
        step["started_at"] = _utc_now_iso()
        time.sleep(0.25)
        step["status"] = "completed"
        step["completed_at"] = _utc_now_iso()
        step["artifact_path"] = f"{report_root}/step_{idx + 1}.json"
        run["artifacts"] = [
            str(row.get("artifact_path", ""))
            for row in steps
            if isinstance(row, dict) and str(row.get("artifact_path", "")).strip()
        ]
        time.sleep(0.15)
    run["status"] = "completed"
    run["completed_at"] = _utc_now_iso()
    created = datetime.fromisoformat(str(run.get("created_at")))
    completed = datetime.fromisoformat(str(run.get("completed_at")))
    elapsed = max(int((completed - created).total_seconds()), 0)
    run["first_meaningful_result_seconds"] = elapsed
    run["meets_under_5_minute_goal"] = elapsed <= 300


def _coerce_stage(stage: str) -> str:
    token = stage.strip().lower()
    if token in _PROMOTION_STAGE_ORDER or token == "halted":
        return token
    return "paper"


def _next_stage(current: str, action: str) -> str:
    stage = _coerce_stage(current)
    if action == "hold":
        return stage
    if action == "halt":
        return "halted"
    if stage == "halted":
        return "paper" if action in {"advance", "rollback"} else stage
    idx = _PROMOTION_STAGE_ORDER.index(stage)
    if action == "rollback":
        return _PROMOTION_STAGE_ORDER[max(idx - 1, 0)]
    if action == "advance":
        return _PROMOTION_STAGE_ORDER[min(idx + 1, len(_PROMOTION_STAGE_ORDER) - 1)]
    return stage


def _enforce_read_limit(request: Request, cache: APICache, identity: APIIdentity) -> None:
    settings = request.app.state.settings
    enforce_rate_limit(
        cache=cache,
        bucket=f"read:{identity.subject}",
        limit=int(settings.read_rate_limit_per_minute),
        window_seconds=60,
    )


def _enforce_write_limit(request: Request, cache: APICache, identity: APIIdentity) -> None:
    settings = request.app.state.settings
    enforce_rate_limit(
        cache=cache,
        bucket=f"write:{identity.subject}",
        limit=int(settings.write_rate_limit_per_minute),
        window_seconds=60,
    )


@router.get("/accounts/{account_id}")
def get_account_summary(
    account_id: str,
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
    persistence: Annotated[APIPersistence | None, Depends(get_persistence)],
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    if persistence is not None:
        account = persistence.get_account(account_id)
    else:
        account = store.accounts.get(account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")
    return with_correlation(request, {"account": account.to_dict()})


@router.put("/accounts/{account_id}")
async def upsert_account_summary(
    account_id: str,
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_operator)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
    hub: Annotated[StreamHub, Depends(get_stream_hub)],
    persistence: Annotated[APIPersistence | None, Depends(get_persistence)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    trace_id, run_id = read_request_correlation(request)
    payload["account_id"] = account_id
    try:
        snapshot = AccountSummary.from_dict(payload)
    except Exception as exc:
        raise _invalid_payload(exc) from exc
    store.accounts[account_id] = snapshot
    if persistence is not None:
        persistence.upsert_account(snapshot)
    await hub.broadcast(
        "risk",
        "account_upsert",
        {"account_id": account_id, "account": snapshot.to_dict()},
        trace_id=trace_id,
        run_id=run_id,
    )
    return with_correlation(request, {"account": snapshot.to_dict()})


@router.get("/portfolio/positions")
def list_positions(
    account_id: Annotated[str, Query(min_length=1)],
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
    persistence: Annotated[APIPersistence | None, Depends(get_persistence)],
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    rows = (
        persistence.list_positions(account_id)
        if persistence is not None
        else store.positions.get(account_id, [])
    )
    return with_correlation(request, {"positions": [item.to_dict() for item in rows]})


@router.post("/portfolio/positions")
async def append_position(
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_operator)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
    hub: Annotated[StreamHub, Depends(get_stream_hub)],
    persistence: Annotated[APIPersistence | None, Depends(get_persistence)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    trace_id, run_id = read_request_correlation(request)
    try:
        snapshot = PositionSnapshot.from_dict(payload)
    except Exception as exc:
        raise _invalid_payload(exc) from exc
    store.positions.setdefault(snapshot.account_id, []).append(snapshot)
    if persistence is not None:
        persistence.append_position(snapshot)
    await hub.broadcast(
        "positions",
        "position_appended",
        {"account_id": snapshot.account_id, "position": snapshot.to_dict()},
        trace_id=trace_id,
        run_id=run_id,
    )
    return with_correlation(request, {"position": snapshot.to_dict()})


@router.get("/execution/orders")
def list_orders(
    account_id: Annotated[str, Query(min_length=1)],
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
    persistence: Annotated[APIPersistence | None, Depends(get_persistence)],
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    rows = (
        persistence.list_orders(account_id) if persistence is not None else store.orders.get(account_id, [])
    )
    return with_correlation(request, {"orders": [item.to_dict() for item in rows]})


@router.post("/execution/orders")
async def append_order(
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_operator)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
    hub: Annotated[StreamHub, Depends(get_stream_hub)],
    persistence: Annotated[APIPersistence | None, Depends(get_persistence)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    trace_id, run_id = read_request_correlation(request)
    try:
        snapshot = OrderSnapshot.from_dict(payload)
    except Exception as exc:
        raise _invalid_payload(exc) from exc
    store.orders.setdefault(snapshot.account_id, []).append(snapshot)
    if persistence is not None:
        persistence.append_order(snapshot)
    await hub.broadcast(
        "orders",
        "order_appended",
        {"account_id": snapshot.account_id, "order": snapshot.to_dict()},
        trace_id=trace_id,
        run_id=run_id,
    )
    return with_correlation(request, {"order": snapshot.to_dict()})


@router.get("/execution/fills")
def list_fills(
    account_id: Annotated[str, Query(min_length=1)],
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
    persistence: Annotated[APIPersistence | None, Depends(get_persistence)],
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    rows = (
        persistence.list_fills(account_id) if persistence is not None else store.fills.get(account_id, [])
    )
    return with_correlation(request, {"fills": [item.to_dict() for item in rows]})


@router.post("/execution/fills")
async def append_fill(
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_operator)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
    hub: Annotated[StreamHub, Depends(get_stream_hub)],
    persistence: Annotated[APIPersistence | None, Depends(get_persistence)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    trace_id, run_id = read_request_correlation(request)
    try:
        snapshot = FillSnapshot.from_dict(payload)
    except Exception as exc:
        raise _invalid_payload(exc) from exc
    store.fills.setdefault(snapshot.account_id, []).append(snapshot)
    if persistence is not None:
        persistence.append_fill(snapshot)
    await hub.broadcast(
        "fills",
        "fill_appended",
        {"account_id": snapshot.account_id, "fill": snapshot.to_dict()},
        trace_id=trace_id,
        run_id=run_id,
    )
    return with_correlation(request, {"fill": snapshot.to_dict()})


@router.get("/pnl/snapshots")
def list_pnl_snapshots(
    account_id: Annotated[str, Query(min_length=1)],
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
    persistence: Annotated[APIPersistence | None, Depends(get_persistence)],
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    rows = (
        persistence.list_pnl_snapshots(account_id)
        if persistence is not None
        else store.pnl_snapshots.get(account_id, [])
    )
    return with_correlation(request, {"snapshots": [item.to_dict() for item in rows]})


@router.post("/pnl/snapshots")
async def append_pnl_snapshot(
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_operator)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
    hub: Annotated[StreamHub, Depends(get_stream_hub)],
    persistence: Annotated[APIPersistence | None, Depends(get_persistence)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    trace_id, run_id = read_request_correlation(request)
    try:
        snapshot = PnLSnapshot.from_dict(payload)
    except Exception as exc:
        raise _invalid_payload(exc) from exc
    store.pnl_snapshots.setdefault(snapshot.account_id, []).append(snapshot)
    if persistence is not None:
        persistence.append_pnl_snapshot(snapshot)
    await hub.broadcast(
        "pnl",
        "pnl_snapshot_appended",
        {"account_id": snapshot.account_id, "snapshot": snapshot.to_dict()},
        trace_id=trace_id,
        run_id=run_id,
    )
    return with_correlation(request, {"snapshot": snapshot.to_dict()})


@router.get("/risk/state/{account_id}")
def get_risk_state(
    account_id: str,
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
    persistence: Annotated[APIPersistence | None, Depends(get_persistence)],
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    snapshot = (
        persistence.get_risk_state(account_id)
        if persistence is not None
        else store.risk_states.get(account_id)
    )
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk state not found.")
    return with_correlation(request, {"risk_state": snapshot.to_dict()})


@router.put("/risk/state/{account_id}")
async def upsert_risk_state(
    account_id: str,
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_operator)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
    hub: Annotated[StreamHub, Depends(get_stream_hub)],
    persistence: Annotated[APIPersistence | None, Depends(get_persistence)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    trace_id, run_id = read_request_correlation(request)
    payload["account_id"] = account_id
    try:
        snapshot = RiskStateSnapshot.from_dict(payload)
    except Exception as exc:
        raise _invalid_payload(exc) from exc
    store.risk_states[account_id] = snapshot
    if persistence is not None:
        persistence.upsert_risk_state(snapshot)
    await hub.broadcast(
        "risk",
        "risk_state_upserted",
        {"account_id": account_id, "risk_state": snapshot.to_dict()},
        trace_id=trace_id,
        run_id=run_id,
    )
    return with_correlation(request, {"risk_state": snapshot.to_dict()})


@router.post("/risk/incidents")
async def append_risk_incident(
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_operator)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
    hub: Annotated[StreamHub, Depends(get_stream_hub)],
    persistence: Annotated[APIPersistence | None, Depends(get_persistence)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    trace_id, run_id = read_request_correlation(request)
    account_id = str(payload.get("account_id", "paper-main")).strip() or "paper-main"
    incident = {
        "account_id": account_id,
        "severity": str(payload.get("severity", "warning")),
        "message": str(payload.get("message", "")).strip(),
        "code": str(payload.get("code", "unspecified")),
        "timestamp": str(payload.get("timestamp", _utc_now_iso())),
        "metadata": dict(payload.get("metadata", {}) or {}),
    }
    store.risk_incidents.setdefault(account_id, []).append(incident)
    if persistence is not None:
        persistence.append_risk_incident(incident)
    await hub.broadcast(
        "risk",
        "risk_incident",
        {"account_id": account_id, "incident": incident},
        trace_id=trace_id,
        run_id=run_id,
    )
    return with_correlation(request, {"incident": incident})


@router.get("/operator/actions")
def list_operator_actions(
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
    persistence: Annotated[APIPersistence | None, Depends(get_persistence)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    if persistence is not None:
        actions = persistence.list_operator_actions(limit=limit)
    else:
        actions = [dict(item) for item in store.operator_actions[:limit]]
    return with_correlation(request, {"actions": actions})


@router.post("/operator/actions")
def append_operator_action(
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_operator)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
    persistence: Annotated[APIPersistence | None, Depends(get_persistence)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    kind = str(payload.get("kind", "")).strip()
    if not kind:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="kind is required")
    entry = {
        "id": str(payload.get("id", f"op_{uuid4().hex[:10]}")),
        "kind": kind,
        "actor": str(payload.get("actor", identity.subject)).strip() or identity.subject,
        "note": str(payload.get("note", "")).strip(),
        "created_at": str(payload.get("created_at", _utc_now_iso())),
    }
    store.operator_actions.insert(0, entry)
    del store.operator_actions[250:]
    if persistence is not None:
        persistence.append_operator_action(entry)
    return with_correlation(request, {"action": entry})


@router.get("/promotions")
def list_promotions(
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
    persistence: Annotated[APIPersistence | None, Depends(get_persistence)],
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    if persistence is not None:
        records = persistence.list_promotion_records()
    else:
        records = [dict(item) for item in store.promotion_records.values()]
    if not records:
        records = [dict(item) for item in APIRuntimeStore.bootstrap().promotion_records.values()]
        for record in records:
            store.promotion_records[str(record.get("strategy_id", ""))] = record
    records = sorted(records, key=lambda row: str(row.get("strategy_id", "")))
    return with_correlation(request, {"records": records})


@router.post("/promotions/actions")
def apply_promotion_action(
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_operator)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
    persistence: Annotated[APIPersistence | None, Depends(get_persistence)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    strategy_id = str(payload.get("strategy_id", "")).strip()
    action = str(payload.get("action", "")).strip().lower()
    if not strategy_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="strategy_id is required")
    if action not in {"advance", "hold", "rollback", "halt"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid action")

    current = store.promotion_records.get(strategy_id) or _default_promotion_record(strategy_id)
    stage_before = _coerce_stage(str(current.get("stage", "paper")))
    stage_after = _next_stage(stage_before, action)
    history = current.get("history", [])
    history_rows = history if isinstance(history, list) else []
    event = {
        "action": action,
        "actor": str(payload.get("actor", identity.subject)).strip() or identity.subject,
        "note": str(payload.get("note", "")).strip(),
        "from_stage": stage_before,
        "to_stage": stage_after,
        "at": _utc_now_iso(),
    }
    updated = {
        **current,
        "strategy_id": strategy_id,
        "stage": stage_after,
        "updated_at": _utc_now_iso(),
        "history": [event, *history_rows][:100],
    }
    store.promotion_records[strategy_id] = updated
    if persistence is not None:
        persistence.upsert_promotion_record(updated)

    records = sorted(
        [dict(item) for item in store.promotion_records.values()],
        key=lambda row: str(row.get("strategy_id", "")),
    )
    return with_correlation(request, {"updated": updated, "records": records})


@router.get("/agent/context")
def get_agent_context(
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
    agent_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    resolved_agent_id = str(agent_id or identity.subject).strip() or identity.subject
    _assert_agent_access(identity, resolved_agent_id)
    policy = _get_agent_policy(store, resolved_agent_id)
    account = store.accounts.get("paper-main")
    risk = store.risk_states.get("paper-main")
    sync_rows = _collect_brokerage_sync_health(store)
    degraded = len([row for row in sync_rows if bool(row.get("fail_closed_trade_block"))])
    promotions = sorted(
        [
            {
                "strategy_id": str(row.get("strategy_id", "")),
                "stage": str(row.get("stage", "")),
                "updated_at": str(row.get("updated_at", "")),
            }
            for row in store.promotion_records.values()
            if isinstance(row, dict)
        ],
        key=lambda row: row["strategy_id"],
    )
    return with_correlation(request, {
        "agent_id": resolved_agent_id,
        "system_facts": {
            "hard_rules": [
                "orders_must_flow_via_risk_aware_router",
                "kill_switch_and_risk_limits_non_bypassable",
                "promotion_stage_skips_disallowed_by_gate_policy",
            ],
            "allowed_actions": sorted(_AGENT_ACTIONS),
        },
        "current_state": {
            "account": account.to_dict() if account is not None else None,
            "risk_state": risk.to_dict() if risk is not None else None,
            "sync_health": {
                "degraded_count": degraded,
                "all_clear": degraded == 0,
            },
            "promotion_stages": promotions,
        },
        "policy": policy,
    })


@router.get("/agent/policies/{agent_id}")
def get_agent_policy(
    agent_id: str,
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    resolved = str(agent_id).strip()
    _assert_agent_access(identity, resolved)
    policy = _get_agent_policy(store, resolved)
    return with_correlation(request, {"policy": policy})


@router.put("/agent/policies/{agent_id}")
def upsert_agent_policy(
    agent_id: str,
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_operator)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    resolved = str(agent_id).strip()
    if not resolved:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="agent_id is required")
    current = _get_agent_policy(store, resolved)
    capabilities = payload.get("capabilities", current.get("capabilities", {}))
    if not isinstance(capabilities, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="capabilities must be an object")
    sanitized_capabilities = {
        "read": bool(capabilities.get("read", True)),
        "propose": bool(capabilities.get("propose", True)),
        "simulate": bool(capabilities.get("simulate", True)),
        "execute": bool(capabilities.get("execute", False)),
        "hooks_manage": bool(capabilities.get("hooks_manage", True)),
    }
    max_pending = int(payload.get("max_pending_intents", current.get("max_pending_intents", 20)))
    risk_budget = float(payload.get("risk_budget_pct", current.get("risk_budget_pct", 2.0)))
    allowed_markets = payload.get("allowed_markets", current.get("allowed_markets", ["crypto"]))
    allowed_actions = payload.get("allowed_actions", current.get("allowed_actions", sorted(_AGENT_ACTIONS)))
    if not isinstance(allowed_markets, list) or not all(isinstance(item, str) for item in allowed_markets):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="allowed_markets must be string array")
    if not isinstance(allowed_actions, list) or not all(isinstance(item, str) for item in allowed_actions):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="allowed_actions must be string array")
    normalized_actions = sorted({str(item).strip().lower() for item in allowed_actions if str(item).strip()})
    unknown_actions = [item for item in normalized_actions if item not in _AGENT_ACTIONS]
    if unknown_actions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"unknown actions: {unknown_actions}")
    updated = {
        "agent_id": resolved,
        "capabilities": sanitized_capabilities,
        "max_pending_intents": max(1, min(max_pending, 500)),
        "risk_budget_pct": max(0.1, min(risk_budget, 100.0)),
        "allowed_markets": sorted({str(item).strip().lower() for item in allowed_markets if str(item).strip()}),
        "allowed_actions": normalized_actions,
        "updated_at": _utc_now_iso(),
        "updated_by": identity.subject,
    }
    store.agent_policies[resolved] = updated
    return with_correlation(request, {"policy": updated})


@router.post("/agent/intents")
def create_agent_intent(
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    resolved_agent_id = str(payload.get("agent_id", identity.subject)).strip() or identity.subject
    _assert_agent_access(identity, resolved_agent_id)
    policy = _get_agent_policy(store, resolved_agent_id)
    _ensure_agent_capability(policy, "propose")
    if _count_pending_intents(store, resolved_agent_id) >= int(policy.get("max_pending_intents", 20)):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="pending intent quota reached")

    errors = _validate_agent_intent_payload(payload)
    if errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"errors": errors})
    action = str(payload.get("action", "")).strip().lower()
    if action not in set(policy.get("allowed_actions", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="action denied by agent policy")
    intent_id = f"intent_{uuid4().hex[:12]}"
    intent = {
        "intent_id": intent_id,
        "agent_id": resolved_agent_id,
        "action": action,
        "strategy_id": str(payload.get("strategy_id", "")).strip(),
        "rationale": str(payload.get("rationale", "")).strip(),
        "supporting_card_ids": list(payload.get("supporting_card_ids", [])),
        "current_metrics": dict(payload.get("current_metrics", {})),
        "gate_checks": dict(payload.get("gate_checks", {})),
        "risk_impact": dict(payload.get("risk_impact", {})),
        "status": "proposed",
        "created_at": _utc_now_iso(),
        "updated_at": _utc_now_iso(),
        "created_by": identity.subject,
    }
    store.agent_intents[intent_id] = intent
    receipt = _record_agent_receipt(
        store,
        receipt_type="intent_proposed",
        intent_id=intent_id,
        agent_id=resolved_agent_id,
        payload={"status": "proposed", "action": action},
    )
    return with_correlation(request, {"intent": intent, "receipt": receipt})


@router.get("/agent/intents/{intent_id}")
def get_agent_intent(
    intent_id: str,
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    intent = store.agent_intents.get(str(intent_id).strip())
    if not isinstance(intent, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="intent not found")
    _assert_agent_access(identity, str(intent.get("agent_id", "")))
    return with_correlation(request, {"intent": intent})


@router.post("/agent/intents/{intent_id}/simulate")
def simulate_agent_intent(
    intent_id: str,
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    intent = store.agent_intents.get(str(intent_id).strip())
    if not isinstance(intent, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="intent not found")
    agent_id = str(intent.get("agent_id", ""))
    _assert_agent_access(identity, agent_id)
    policy = _get_agent_policy(store, agent_id)
    _ensure_agent_capability(policy, "simulate")
    if str(intent.get("action", "")) not in set(policy.get("allowed_actions", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="action denied by agent policy")
    checks = _build_agent_gate_checks(intent, store)
    simulation = {
        "simulated_at": _utc_now_iso(),
        "passed": bool(checks.get("passed", False)),
        "gate_checks": checks,
    }
    intent["last_simulation"] = simulation
    intent["status"] = "simulated" if simulation["passed"] else "rejected"
    intent["updated_at"] = _utc_now_iso()
    store.agent_intents[str(intent.get("intent_id"))] = intent
    receipt = _record_agent_receipt(
        store,
        receipt_type="intent_simulated",
        intent_id=str(intent.get("intent_id", "")),
        agent_id=agent_id,
        payload={"passed": simulation["passed"], "gate_checks": checks},
    )
    return with_correlation(request, {"intent": intent, "simulation": simulation, "receipt": receipt})


@router.post("/agent/intents/{intent_id}/execute")
def execute_agent_intent(
    intent_id: str,
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    if not _identity_is_operator(identity):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="operator role required for execute")
    intent = store.agent_intents.get(str(intent_id).strip())
    if not isinstance(intent, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="intent not found")
    agent_id = str(intent.get("agent_id", ""))
    policy = _get_agent_policy(store, agent_id)
    _ensure_agent_capability(policy, "execute")

    checks = _build_agent_gate_checks(intent, store)
    simulation = intent.get("last_simulation", {})
    simulated_passed = bool(simulation.get("passed", False)) if isinstance(simulation, dict) else False
    if not simulated_passed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="intent requires successful simulation")
    if not bool(checks.get("passed", False)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "gate checks failed", "reasons": checks.get("blocked_reasons", [])},
        )

    strategy_id = str(intent.get("strategy_id", ""))
    action = str(intent.get("action", "hold")).strip().lower()
    current = store.promotion_records.get(strategy_id) or _default_promotion_record(strategy_id)
    stage_before = _coerce_stage(str(current.get("stage", "paper")))
    stage_after = _proposed_stage_for_action(action=action, current_stage=stage_before)
    history_rows = current.get("history", [])
    history = history_rows if isinstance(history_rows, list) else []
    event = {
        "action": action,
        "actor": identity.subject,
        "note": "agent execute",
        "from_stage": stage_before,
        "to_stage": stage_after,
        "at": _utc_now_iso(),
        "intent_id": str(intent.get("intent_id", "")),
    }
    updated = {
        **current,
        "strategy_id": strategy_id,
        "stage": stage_after,
        "updated_at": _utc_now_iso(),
        "history": [event, *history][:100],
    }
    store.promotion_records[strategy_id] = updated
    intent["status"] = "executed"
    intent["executed_at"] = _utc_now_iso()
    intent["updated_at"] = _utc_now_iso()
    store.agent_intents[str(intent.get("intent_id"))] = intent
    receipt = _record_agent_receipt(
        store,
        receipt_type="intent_executed",
        intent_id=str(intent.get("intent_id", "")),
        agent_id=agent_id,
        payload={"stage_before": stage_before, "stage_after": stage_after, "strategy_id": strategy_id},
    )
    return with_correlation(request, {"intent": intent, "promotion": updated, "receipt": receipt})


@router.get("/agent/receipts/{receipt_id}")
def get_agent_receipt(
    receipt_id: str,
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    receipt = store.agent_receipts.get(str(receipt_id).strip())
    if not isinstance(receipt, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="receipt not found")
    _assert_agent_access(identity, str(receipt.get("agent_id", "")))
    return with_correlation(request, {"receipt": receipt})


@router.get("/agent/hooks")
def list_agent_hooks(
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
    agent_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    resolved_agent_id = str(agent_id or identity.subject).strip() or identity.subject
    _assert_agent_access(identity, resolved_agent_id)
    rows = [
        dict(row)
        for row in store.agent_hooks.values()
        if isinstance(row, dict) and str(row.get("agent_id", "")) == resolved_agent_id and str(row.get("status", "")) != "deleted"
    ]
    rows.sort(key=lambda row: str(row.get("hook_id", "")))
    return with_correlation(request, {"hooks": rows, "count": len(rows)})


@router.post("/agent/hooks")
def create_agent_hook(
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    resolved_agent_id = str(payload.get("agent_id", identity.subject)).strip() or identity.subject
    _assert_agent_access(identity, resolved_agent_id)
    policy = _get_agent_policy(store, resolved_agent_id)
    _ensure_agent_capability(policy, "hooks_manage")

    event_type = str(payload.get("event_type", "")).strip().lower()
    if event_type not in _AGENT_HOOK_EVENTS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported event_type")
    target_url_raw = str(payload.get("target_url", "")).strip()
    if not target_url_raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_url is required")
    target_url, host = _normalize_hook_url(target_url_raw)
    existing = [
        row
        for row in store.agent_hooks.values()
        if isinstance(row, dict) and str(row.get("agent_id", "")) == resolved_agent_id and str(row.get("status", "")) != "deleted"
    ]
    if len(existing) >= 20:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="hook quota reached")
    hook = {
        "hook_id": f"hook_{uuid4().hex[:10]}",
        "agent_id": resolved_agent_id,
        "event_type": event_type,
        "target_url": target_url,
        "target_host": host,
        "status": "active",
        "secret_fingerprint": _fingerprint_secret(str(payload.get("secret", "")).strip()),
        "retry_max": max(0, min(int(payload.get("retry_max", 3)), 10)),
        "backoff_seconds": max(1, min(int(payload.get("backoff_seconds", 5)), 300)),
        "created_at": _utc_now_iso(),
        "updated_at": _utc_now_iso(),
    }
    store.agent_hooks[hook["hook_id"]] = hook
    return with_correlation(request, {"hook": hook})


@router.delete("/agent/hooks/{hook_id}")
def delete_agent_hook(
    hook_id: str,
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    row = store.agent_hooks.get(str(hook_id).strip())
    if not isinstance(row, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="hook not found")
    _assert_agent_access(identity, str(row.get("agent_id", "")))
    row["status"] = "deleted"
    row["deleted_at"] = _utc_now_iso()
    row["updated_at"] = _utc_now_iso()
    store.agent_hooks[str(hook_id).strip()] = row
    return with_correlation(request, {"hook": row})


@router.post("/integrations/brokerage/plaid/link/start")
def start_plaid_link(
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    requested_scope = str(payload.get("scope", "read_only")).strip().lower()
    scope = requested_scope if requested_scope in {"read_only", "trade_enabled"} else "read_only"
    if scope == "trade_enabled":
        scope = "read_only"
    institution = str(payload.get("institution", "demo_broker")).strip() or "demo_broker"
    link_id = f"plaid_link_{uuid4().hex[:10]}"
    link_token = f"link-sandbox-{uuid4().hex[:12]}"
    row = {
        "link_id": link_id,
        "provider": "plaid",
        "institution": institution,
        "status": "link_token_created",
        "scope": scope,
        "permissions": ["accounts:read"],
        "trade_permission_enabled": False,
        "created_by": identity.subject,
        "created_at": _utc_now_iso(),
        "updated_at": _utc_now_iso(),
        "last_sync_at": "",
        "stale_after_seconds": _BROKERAGE_STALE_AFTER_SECONDS,
        "token_fingerprint": "",
    }
    store.brokerage_links[link_id] = row
    return with_correlation(request, {
        "link_id": link_id,
        "link_token": link_token,
        "provider": "plaid",
        "scope": scope,
        "permissions": row["permissions"],
        "trade_permission_enabled": False,
        "next": ["complete_link"],
    })


@router.post("/integrations/brokerage/plaid/link/complete")
def complete_plaid_link(
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    link_id = str(payload.get("link_id", "")).strip()
    public_token = str(payload.get("public_token", "")).strip()
    if not link_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="link_id is required")
    if not public_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="public_token is required")

    existing = store.brokerage_links.get(link_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="link_id not found")

    requested_trade = bool(payload.get("request_trade_permission", False))
    acknowledge = bool(payload.get("acknowledge_trade_risk", False))
    if requested_trade and not acknowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="acknowledge_trade_risk=true required for trade permission",
        )

    connection_id = f"conn_{uuid4().hex[:10]}"
    institution = str(payload.get("institution", existing.get("institution", "demo_broker"))).strip() or "demo_broker"
    accounts = _build_demo_brokerage_accounts(connection_id=connection_id, institution=institution)
    now_iso = _utc_now_iso()
    updated = {
        **existing,
        "connection_id": connection_id,
        "institution": institution,
        "status": "connected",
        "updated_at": now_iso,
        "last_sync_at": now_iso,
        "token_fingerprint": _fingerprint_secret(public_token),
        "trade_permission_enabled": bool(requested_trade and acknowledge),
        "permissions": ["accounts:read"] + (["orders:trade"] if requested_trade and acknowledge else []),
        "completed_by": identity.subject,
    }
    store.brokerage_links[link_id] = updated
    store.brokerage_accounts[connection_id] = accounts
    sync_state = _compute_sync_state(updated)
    return with_correlation(request, {
        "connection": updated,
        "accounts": accounts,
        "sync": sync_state,
    })


@router.get("/integrations/brokerage/accounts")
def list_brokerage_accounts(
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    rows = _collect_brokerage_accounts(store)
    return with_correlation(request, {
        "accounts": rows,
        "totals": _portfolio_totals(rows),
    })


@router.get("/integrations/brokerage/sync-health")
def get_brokerage_sync_health(
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    rows = _collect_brokerage_sync_health(store)
    degraded = [row for row in rows if bool(row.get("fail_closed_trade_block"))]
    return with_correlation(request, {
        "connections": rows,
        "degraded_count": len(degraded),
        "all_clear": len(degraded) == 0,
    })


@router.post("/integrations/brokerage/sync")
def sync_brokerage_accounts(
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_operator)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    target = str(payload.get("link_id", "")).strip()
    now_iso = _utc_now_iso()
    touched: list[str] = []
    for link_id, row in list(store.brokerage_links.items()):
        if target and link_id != target:
            continue
        if not isinstance(row, dict) or str(row.get("status", "")) != "connected":
            continue
        row["last_sync_at"] = now_iso
        row["updated_at"] = now_iso
        store.brokerage_links[link_id] = row
        touched.append(link_id)
        connection_id = str(row.get("connection_id", "")).strip()
        if connection_id and connection_id in store.brokerage_accounts:
            refreshed: list[dict[str, Any]] = []
            for account in store.brokerage_accounts[connection_id]:
                entry = dict(account)
                entry["as_of"] = now_iso
                refreshed.append(entry)
            store.brokerage_accounts[connection_id] = refreshed
    if target and not touched:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="link_id not found")
    return with_correlation(request, {"synced_links": touched, "synced_at": now_iso})


@router.get("/studio/terminal")
def get_personal_terminal(
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    profile = dict(store.terminal_profiles.get(identity.subject, {}))
    defaults = {
        "density": "guided",
        "watchlist": ["BTC-USD", "ETH-USD"],
        "refresh_seconds": 5,
        "theme": "system",
    }
    merged = {**defaults, **profile}
    account_rows = _collect_brokerage_accounts(store)
    sync_rows = _collect_brokerage_sync_health(store)
    degraded_count = len([row for row in sync_rows if bool(row.get("fail_closed_trade_block"))])
    return with_correlation(request, {
        "subject": identity.subject,
        "always_on": True,
        "profile": merged,
        "portfolio_totals": _portfolio_totals(account_rows),
        "sync_health": {
            "degraded_count": degraded_count,
            "all_clear": degraded_count == 0,
        },
        "next_actions": [
            "connect_brokerage_accounts" if not account_rows else "open_execution_console",
            "review_sync_health",
            "run_paper_campaign",
        ],
        "generated_at": _utc_now_iso(),
    })


@router.put("/studio/terminal/preferences")
def update_terminal_preferences(
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    allowed = {"density", "watchlist", "refresh_seconds", "theme"}
    sanitized: dict[str, Any] = {}
    for key in allowed:
        if key in payload:
            sanitized[key] = payload[key]
    existing = dict(store.terminal_profiles.get(identity.subject, {}))
    updated = {**existing, **sanitized, "updated_at": _utc_now_iso()}
    store.terminal_profiles[identity.subject] = updated
    return with_correlation(request, {"profile": updated})


@router.get("/assistant/audit")
def list_assistant_audit(
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    rows = [dict(item) for item in store.assistant_audit if str(item.get("subject", "")) == identity.subject]
    rows = rows[:limit]
    return with_correlation(request, {"events": rows, "count": len(rows)})


@router.post("/assistant/turn")
def assistant_turn(
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    message = str(payload.get("message", "")).strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message is required")

    message_lc = message.lower()
    requested_action = str(payload.get("requested_action", "")).strip().lower()
    capital_affecting = any(token in message_lc for token in _CAPITAL_ACTION_TOKENS) or requested_action in {
        "trade",
        "rebalance",
        "execute",
    }
    suggestions: list[dict[str, str]] = []
    if "risk" in message_lc or "kill" in message_lc:
        suggestions.append({"title": "Open risk surface", "href": "/dashboard/risk"})
    if "order" in message_lc or "fill" in message_lc or "reject" in message_lc:
        suggestions.append({"title": "Inspect order truth", "href": "/dashboard/order-truth"})
    if "benchmark" in message_lc or "result" in message_lc:
        suggestions.append({"title": "Review benchmarks", "href": "/dashboard/benchmarks"})
    if not suggestions:
        suggestions = [
            {"title": "Open command center", "href": "/dashboard"},
            {"title": "Start guided onboarding", "href": "/onboarding"},
        ]
    audit_row = {
        "id": f"ast_{uuid4().hex[:10]}",
        "subject": identity.subject,
        "message": message,
        "requested_action": requested_action or "analysis",
        "capital_affecting": capital_affecting,
        "requires_confirmation": capital_affecting,
        "executed": False,
        "timestamp": _utc_now_iso(),
        "suggestion_count": len(suggestions),
    }
    store.assistant_audit.insert(0, audit_row)
    del store.assistant_audit[500:]
    return with_correlation(request, {
        "assistant_message": (
            "Recommendation generated using constrained operator policy. "
            "Review linked surfaces before any capital-affecting action."
        ),
        "suggestions": suggestions,
        "action_policy": {
            "mode": "analysis_only" if not capital_affecting else "requires_confirmation",
            "capital_affecting": capital_affecting,
            "executed": False,
        },
        "audit_id": audit_row["id"],
    })


@router.post("/onboarding/runs")
def start_onboarding_run(
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    experience = _normalize_experience(payload.get("experience"))
    automation = _normalize_automation(payload.get("automation"))
    capital_usd = _normalize_capital(payload.get("capital_usd", payload.get("capitalUsd")))
    plan = _build_onboarding_plan(
        experience=experience,
        automation=automation,
        capital_usd=capital_usd,
    )
    run_id = f"run_{uuid4().hex[:10]}"
    run = _build_onboarding_run(run_id=run_id, commands=[str(item) for item in plan["commands"]])
    store.onboarding_runs[run_id] = run

    worker = threading.Thread(
        target=_simulate_onboarding_progress,
        args=(store, run_id),
        daemon=True,
    )
    worker.start()

    return with_correlation(request, {"run": run, "plan": plan})


@router.get("/onboarding/runs/{run_id}")
def get_onboarding_run(
    run_id: str,
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    store: Annotated[APIRuntimeStore, Depends(get_store)],
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    run = store.onboarding_runs.get(str(run_id).strip())
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    return with_correlation(request, {"run": run})


@router.get("/ops/reference-performance")
def get_reference_performance(
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    payload = load_reference_performance()
    payload["provenance"] = load_reference_provenance()
    return with_correlation(request, payload)


@router.get("/ops/execution-quality")
def get_execution_quality(
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    limit: Annotated[int, Query(ge=1, le=2000)] = 200,
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    payload = summarize_execution_quality(limit=limit)
    return with_correlation(request, payload)


@router.get("/ops/order-truth")
def get_order_truth(
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    order_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    payload = build_order_truth(order_id=order_id)
    payload["rows"] = payload["rows"][:100]
    return with_correlation(request, payload)


@router.get("/ops/replay")
def get_replay(
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 120,
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    return with_correlation(request, summarize_replay(limit=limit))


@router.get("/ops/template-gallery")
def get_template_gallery(
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
    mode: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 40,
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    artifacts = list_template_run_artifacts(mode=mode, limit=limit)
    return with_correlation(request, {"count": len(artifacts), "artifacts": artifacts})


@router.get("/ops/data-seed/presets")
def get_data_seed_presets(
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    return with_correlation(request, {"presets": data_seed_presets()})


@router.post("/ops/data-seed/run")
def run_data_seed(
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_operator)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    command = build_data_seed_command(payload)
    execute = bool(payload.get("execute", False))
    if not execute:
        return with_correlation(request, {
            "dry_run": True,
            "command": [sys.executable, *command],
            "note": "Set execute=true to run bounded data bootstrap with cache/checksum/retry controls.",
        })
    result = run_python_command(command, timeout_seconds=180)
    output_lines = [line for line in str(result.get("stdout", "")).splitlines() if line.strip()]
    return with_correlation(request, {"dry_run": False, **result, "output_lines": output_lines})


@router.post("/ops/notify/test")
def run_notify_test(
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_operator)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
) -> dict[str, Any]:
    _enforce_write_limit(request, cache, identity)
    command = build_notify_command(payload)
    execute = bool(payload.get("execute", False))
    if not execute:
        return with_correlation(request, {"dry_run": True, "command": [sys.executable, *command]})
    result = run_python_command(command, timeout_seconds=90)
    return with_correlation(request, {"dry_run": False, **result, "parsed": parse_last_json_line(str(result.get("stdout", "")))})
