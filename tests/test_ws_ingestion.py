"""Tests for websocket ingestion service and reconnect behavior."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from execution.live_ops_controls import WebSocketConnectionManager
from execution.risk_aware_router import RiskAwareRouter, VenueClient
from execution.stream_contracts import build_stream_registry
from execution.ws_ingestion import StreamIngestionStore, WebSocketIngestionService
from risk.kill_switches import RiskLimits


class _Clock:
    def __init__(self, now: float = 0.0):
        self.now = float(now)

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += float(seconds)


class _Adapter:
    def stream_descriptors(self):
        return build_stream_registry(
            market_url="wss://market",
            order_url="wss://order",
            fill_url="wss://fill",
            transport="websocket",
            heartbeat_seconds=15.0,
        )


def _router(tmp_path: Path) -> RiskAwareRouter:
    router = RiskAwareRouter(
        risk_config=RiskLimits(),
        broker_config={"enabled": True, "live_execution": False},
        tca_db_path=str(tmp_path / "tca.csv"),
    )
    router.market_venues = {
        "binance": VenueClient(
            market="crypto",
            venue="binance",
            symbols=["BTCUSDT"],
            adapter=_Adapter(),
            connected=True,
            is_stub=False,
        )
    }
    return router


def test_ws_ingestion_collect_once_persists_market_order_fill_events(tmp_path):
    router = _router(tmp_path)
    store = StreamIngestionStore(events_path=str(tmp_path / "ws_events.jsonl"))

    async def fetcher(venue: str, channel: str, _url: str):
        return [{"venue": venue, "channel": channel, "seq": 1}]

    svc = WebSocketIngestionService(router=router, store=store, fetcher=fetcher)
    payload = asyncio.run(svc.collect_once())

    assert payload["events_written"] == 3
    assert payload["market_events"] == 1
    assert payload["order_events"] == 1
    assert payload["fill_events"] == 1

    rows = [
        json.loads(line)
        for line in store.events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    channels = {row["channel"] for row in rows}
    assert channels == {"market", "order", "fill"}


def test_ws_ingestion_uses_backoff_after_disconnect(tmp_path):
    router = _router(tmp_path)
    store = StreamIngestionStore(events_path=str(tmp_path / "ws_events.jsonl"))
    clock = _Clock(10.0)
    ws_manager = WebSocketConnectionManager(
        base_backoff_seconds=2.0,
        max_backoff_seconds=10.0,
        clock=clock,
    )

    attempts = {"count": 0}

    async def flaky_fetcher(_venue: str, _channel: str, _url: str):
        attempts["count"] += 1
        if attempts["count"] <= 3:
            raise RuntimeError("network_down")
        return [{"ok": True}]

    svc = WebSocketIngestionService(
        router=router,
        store=store,
        ws_manager=ws_manager,
        fetcher=flaky_fetcher,
    )

    first = asyncio.run(svc.collect_once())
    second = asyncio.run(svc.collect_once())
    clock.advance(2.1)
    third = asyncio.run(svc.collect_once())

    assert first["events_written"] == 0
    assert first["disconnected_streams"] >= 1
    # No reconnect before backoff expiry.
    assert second["connected_streams"] == 0
    assert third["connected_streams"] >= 1
