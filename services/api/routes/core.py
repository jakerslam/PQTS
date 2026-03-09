"""Core REST endpoints for account, portfolio, execution, PnL, and risk resources."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

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
    return {"account": account.to_dict()}


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
    )
    return {"account": snapshot.to_dict()}


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
    return {"positions": [item.to_dict() for item in rows]}


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
    )
    return {"position": snapshot.to_dict()}


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
    return {"orders": [item.to_dict() for item in rows]}


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
    )
    return {"order": snapshot.to_dict()}


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
    return {"fills": [item.to_dict() for item in rows]}


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
    )
    return {"fill": snapshot.to_dict()}


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
    return {"snapshots": [item.to_dict() for item in rows]}


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
    )
    return {"snapshot": snapshot.to_dict()}


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
    return {"risk_state": snapshot.to_dict()}


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
    )
    return {"risk_state": snapshot.to_dict()}


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
    )
    return {"incident": incident}
