"""Realtime WebSocket channels for execution and risk streams."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from services.api.auth import resolve_identity_for_token
from services.api.correlation import RUN_HEADER, TRACE_HEADER, build_run_id, build_trace_id
from services.api.state import APIRuntimeStore, StreamHub

router = APIRouter()


def _account_from_websocket(websocket: WebSocket) -> str:
    return websocket.query_params.get("account_id", "paper-main")


def _resolve_token(websocket: WebSocket) -> tuple[str, str]:
    qp = websocket.query_params.get("token")
    if qp:
        return qp, "query"
    session = websocket.headers.get("x-session-token")
    if session:
        return session, "session"
    auth = websocket.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip(), "bearer"
    return "", ""


def _resolve_ws_correlation(websocket: WebSocket) -> tuple[str, str]:
    trace_id = websocket.query_params.get("trace_id", "").strip()
    run_id = websocket.query_params.get("run_id", "").strip()
    if not trace_id:
        trace_id = websocket.headers.get(TRACE_HEADER, "").strip() or build_trace_id()
    if not run_id:
        run_id = websocket.headers.get(RUN_HEADER, "").strip() or build_run_id()
    return trace_id, run_id


async def _authenticate_websocket(websocket: WebSocket) -> bool:
    token_store = getattr(websocket.app.state, "token_store", {})
    token, scheme = _resolve_token(websocket)
    identity = resolve_identity_for_token(token, token_store=token_store, auth_scheme=scheme)
    if identity is None:
        await websocket.close(code=4401)
        return False
    return True


async def _serve_channel(
    websocket: WebSocket,
    *,
    channel: str,
    snapshot: Callable[[APIRuntimeStore, str], dict[str, Any]],
) -> None:
    if not await _authenticate_websocket(websocket):
        return

    store: APIRuntimeStore = websocket.app.state.store
    hub: StreamHub = websocket.app.state.stream_hub
    account_id = _account_from_websocket(websocket)
    trace_id, run_id = _resolve_ws_correlation(websocket)

    await hub.connect(channel, websocket)
    try:
        await websocket.send_json(
            {
                "channel": channel,
                "event": "snapshot",
                "payload": snapshot(store, account_id),
                "trace_id": trace_id,
                "run_id": run_id,
            }
        )
        while True:
            _ = await websocket.receive_text()
            await websocket.send_json(
                {
                    "channel": channel,
                    "event": "heartbeat",
                    "payload": snapshot(store, account_id),
                    "trace_id": trace_id,
                    "run_id": run_id,
                }
            )
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(channel, websocket)


def _orders_snapshot(store: APIRuntimeStore, account_id: str) -> dict[str, Any]:
    return {"orders": [row.to_dict() for row in store.orders.get(account_id, [])]}


def _fills_snapshot(store: APIRuntimeStore, account_id: str) -> dict[str, Any]:
    return {"fills": [row.to_dict() for row in store.fills.get(account_id, [])]}


def _positions_snapshot(store: APIRuntimeStore, account_id: str) -> dict[str, Any]:
    return {"positions": [row.to_dict() for row in store.positions.get(account_id, [])]}


def _pnl_snapshot(store: APIRuntimeStore, account_id: str) -> dict[str, Any]:
    return {"snapshots": [row.to_dict() for row in store.pnl_snapshots.get(account_id, [])]}


def _risk_snapshot(store: APIRuntimeStore, account_id: str) -> dict[str, Any]:
    risk = store.risk_states.get(account_id)
    return {
        "risk_state": risk.to_dict() if risk is not None else None,
        "incidents": list(store.risk_incidents.get(account_id, [])),
    }


@router.websocket("/ws/orders")
async def ws_orders(websocket: WebSocket) -> None:
    await _serve_channel(websocket, channel="orders", snapshot=_orders_snapshot)


@router.websocket("/ws/fills")
async def ws_fills(websocket: WebSocket) -> None:
    await _serve_channel(websocket, channel="fills", snapshot=_fills_snapshot)


@router.websocket("/ws/positions")
async def ws_positions(websocket: WebSocket) -> None:
    await _serve_channel(websocket, channel="positions", snapshot=_positions_snapshot)


@router.websocket("/ws/pnl")
async def ws_pnl(websocket: WebSocket) -> None:
    await _serve_channel(websocket, channel="pnl", snapshot=_pnl_snapshot)


@router.websocket("/ws/risk")
async def ws_risk(websocket: WebSocket) -> None:
    await _serve_channel(websocket, channel="risk", snapshot=_risk_snapshot)
