"""In-memory runtime state for core API resources."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import Request, WebSocket

from contracts.api import (
    AccountSummary,
    FillSnapshot,
    OrderSnapshot,
    PnLSnapshot,
    PositionDirection,
    PositionSnapshot,
    RiskLevel,
    RiskStateSnapshot,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class APIRuntimeStore:
    accounts: dict[str, AccountSummary] = field(default_factory=dict)
    positions: dict[str, list[PositionSnapshot]] = field(default_factory=dict)
    orders: dict[str, list[OrderSnapshot]] = field(default_factory=dict)
    fills: dict[str, list[FillSnapshot]] = field(default_factory=dict)
    pnl_snapshots: dict[str, list[PnLSnapshot]] = field(default_factory=dict)
    risk_states: dict[str, RiskStateSnapshot] = field(default_factory=dict)
    risk_incidents: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    operator_actions: list[dict[str, Any]] = field(default_factory=list)
    promotion_records: dict[str, dict[str, Any]] = field(default_factory=dict)
    onboarding_runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    brokerage_links: dict[str, dict[str, Any]] = field(default_factory=dict)
    brokerage_accounts: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    terminal_profiles: dict[str, dict[str, Any]] = field(default_factory=dict)
    assistant_audit: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def bootstrap(cls) -> "APIRuntimeStore":
        now = _utc_now()
        now_iso = now.isoformat()
        account = AccountSummary(
            account_id="paper-main",
            cash=100_000.0,
            equity=100_000.0,
            buying_power=300_000.0,
            margin_used=0.0,
        )
        position = PositionSnapshot(
            position_id="pos-1",
            account_id=account.account_id,
            symbol="BTC-USD",
            direction=PositionDirection.FLAT,
            quantity=0.0,
            avg_price=0.0,
            mark_price=0.0,
            market_value=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            as_of=now,
        )
        pnl = PnLSnapshot(
            account_id=account.account_id,
            period_start=now,
            period_end=now,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            gross_pnl=0.0,
            net_pnl=0.0,
            fees=0.0,
            as_of=now,
        )
        risk = RiskStateSnapshot(
            account_id=account.account_id,
            risk_level=RiskLevel.NORMAL,
            max_drawdown=0.0,
            current_drawdown=0.0,
            var_95=0.0,
            exposure=0.0,
            kill_switch_active=False,
            reasons=[],
            as_of=now,
        )
        return cls(
            accounts={account.account_id: account},
            positions={account.account_id: [position]},
            orders={account.account_id: []},
            fills={account.account_id: []},
            pnl_snapshots={account.account_id: [pnl]},
            risk_states={account.account_id: risk},
            risk_incidents={account.account_id: []},
            operator_actions=[],
            promotion_records={
                "funding_arbitrage": {
                    "strategy_id": "funding_arbitrage",
                    "stage": "paper",
                    "capital_allocation_pct": 2.0,
                    "rollback_trigger": "reject_rate>0.30 or slippage_mape_pct>25",
                    "updated_at": now_iso,
                    "history": [],
                },
                "market_making": {
                    "strategy_id": "market_making",
                    "stage": "paper",
                    "capital_allocation_pct": 2.0,
                    "rollback_trigger": "reject_rate>0.30 or slippage_mape_pct>25",
                    "updated_at": now_iso,
                    "history": [],
                },
                "trend_following": {
                    "strategy_id": "trend_following",
                    "stage": "paper",
                    "capital_allocation_pct": 2.0,
                    "rollback_trigger": "reject_rate>0.30 or slippage_mape_pct>25",
                    "updated_at": now_iso,
                    "history": [],
                },
            },
            onboarding_runs={},
            brokerage_links={},
            brokerage_accounts={},
            terminal_profiles={},
            assistant_audit=[],
        )


def get_store(request: Request) -> APIRuntimeStore:
    store = getattr(request.app.state, "store", None)
    if isinstance(store, APIRuntimeStore):
        return store
    fallback = APIRuntimeStore.bootstrap()
    request.app.state.store = fallback
    return fallback


@dataclass
class StreamHub:
    _channels: dict[str, set[WebSocket]] = field(
        default_factory=lambda: {
            "orders": set(),
            "fills": set(),
            "positions": set(),
            "pnl": set(),
            "risk": set(),
        }
    )
    _sse_channels: dict[str, set[asyncio.Queue[dict[str, Any]]]] = field(
        default_factory=lambda: {
            "orders": set(),
            "fills": set(),
            "positions": set(),
            "pnl": set(),
            "risk": set(),
        }
    )
    _sse_guard: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def connect(self, channel: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._channels.setdefault(channel, set()).add(websocket)

    def disconnect(self, channel: str, websocket: WebSocket) -> None:
        self._channels.setdefault(channel, set()).discard(websocket)

    async def subscribe_sse(
        self,
        channel: str,
        *,
        max_queue_size: int = 256,
    ) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=max(1, int(max_queue_size)))
        async with self._sse_guard:
            self._sse_channels.setdefault(channel, set()).add(queue)
        return queue

    async def unsubscribe_sse(self, channel: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._sse_guard:
            self._sse_channels.setdefault(channel, set()).discard(queue)

    async def broadcast(
        self,
        channel: str,
        event: str,
        payload: dict[str, Any],
        *,
        trace_id: str | None = None,
        run_id: str | None = None,
    ) -> None:
        listeners = list(self._channels.get(channel, set()))
        dead: list[WebSocket] = []
        message = {
            "channel": channel,
            "event": event,
            "payload": payload,
            "timestamp": _utc_now().isoformat(),
            "trace_id": trace_id,
            "run_id": run_id,
        }
        for websocket in listeners:
            try:
                await websocket.send_json(message)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(channel, websocket)
        sse_listeners = list(self._sse_channels.get(channel, set()))
        for queue in sse_listeners:
            packet = dict(message)
            try:
                if queue.full():
                    try:
                        _ = queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                queue.put_nowait(packet)
            except asyncio.QueueFull:
                continue


def get_stream_hub(request: Request) -> StreamHub:
    hub = getattr(request.app.state, "stream_hub", None)
    if isinstance(hub, StreamHub):
        return hub
    fallback = StreamHub()
    request.app.state.stream_hub = fallback
    return fallback
