"""Core REST endpoints for account, portfolio, execution, PnL, and risk resources."""

from __future__ import annotations

import sys
import threading
import time
from datetime import datetime, timezone
from typing import Annotated, Any
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
from services.api.persistence import APIPersistence, get_persistence
from services.api.state import APIRuntimeStore, StreamHub, get_store, get_stream_hub
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


def _default_promotion_record(strategy_id: str) -> dict[str, Any]:
    return {
        "strategy_id": strategy_id,
        "stage": "paper",
        "capital_allocation_pct": 2.0,
        "rollback_trigger": "reject_rate>0.30 or slippage_mape_pct>25",
        "updated_at": _utc_now_iso(),
        "history": [],
    }


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


@router.post("/assistant/turn")
def assistant_turn(
    payload: dict[str, Any],
    identity: Annotated[APIIdentity, Depends(require_identity)],
    request: Request,
    cache: Annotated[APICache, Depends(get_cache)],
) -> dict[str, Any]:
    _enforce_read_limit(request, cache, identity)
    message = str(payload.get("message", "")).strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message is required")

    message_lc = message.lower()
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
    return with_correlation(request, {
        "assistant_message": (
            "Recommendation generated using constrained operator policy. "
            "Review linked surfaces before any capital-affecting action."
        ),
        "suggestions": suggestions,
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
