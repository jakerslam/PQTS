"""Deterministic websocket-ingestion orchestrator for market/order/fill streams."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from execution.live_ops_controls import WebSocketConnectionManager
from execution.risk_aware_router import RiskAwareRouter


@dataclass(frozen=True)
class StreamIngestionEvent:
    event_id: str
    timestamp: str
    venue: str
    channel: str
    url: str
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StreamIngestionStore:
    """Append-only JSONL event sink for websocket-ingestion payloads."""

    def __init__(self, events_path: str = "data/analytics/ws_ingestion_events.jsonl"):
        self.events_path = Path(events_path)
        self.events_path.parent.mkdir(parents=True, exist_ok=True)

    def append_many(self, events: List[StreamIngestionEvent]) -> None:
        if not events:
            return
        with self.events_path.open("a", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")


Fetcher = Callable[[str, str, str], Awaitable[List[Dict[str, Any]]]]


class WebSocketIngestionService:
    """
    Ingest stream payloads for market/order/fill channels.

    This service focuses on deterministic persistence + socket health behavior;
    transport adapters can be swapped behind the async fetcher callback.
    """

    def __init__(
        self,
        *,
        router: RiskAwareRouter,
        store: Optional[StreamIngestionStore] = None,
        ws_manager: Optional[WebSocketConnectionManager] = None,
        fetcher: Optional[Fetcher] = None,
    ):
        self.router = router
        self.store = store or StreamIngestionStore()
        self.ws_manager = ws_manager or WebSocketConnectionManager()
        self.fetcher = fetcher or self._default_fetcher

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _event_id(*parts: object) -> str:
        payload = "|".join(str(part) for part in parts)
        token = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]
        return f"ws_{token}"

    @staticmethod
    async def _default_fetcher(_venue: str, _channel: str, _url: str) -> List[Dict[str, Any]]:
        # Default to no-op in deterministic test/paper environments.
        return []

    def _socket_key(self, venue: str, channel: str) -> str:
        return f"{venue}:{channel}"

    def _ensure_registered(self, socket_key: str, url: str) -> None:
        try:
            self.ws_manager.get(socket_key)
        except KeyError:
            self.ws_manager.register(socket_key, str(url))

    async def collect_once(self) -> Dict[str, Any]:
        registry = self.router.get_stream_registry()
        now = self._utc_now_iso()
        events: List[StreamIngestionEvent] = []
        counts = {"market": 0, "order": 0, "fill": 0}
        connected = 0
        disconnected = 0

        for venue, payload in sorted(registry.items()):
            if not isinstance(payload, dict) or not bool(payload.get("available", False)):
                continue
            streams = payload.get("streams", {})
            if not isinstance(streams, dict):
                continue

            for channel in ("market", "order", "fill"):
                descriptor = streams.get(channel, {})
                if not isinstance(descriptor, dict):
                    continue
                url = str(descriptor.get("url", "")).strip()
                if not url:
                    continue

                socket_key = self._socket_key(venue, channel)
                self._ensure_registered(socket_key, url)

                if not self.ws_manager.can_reconnect(socket_key):
                    disconnected += 1
                    continue

                try:
                    rows = await self.fetcher(venue, channel, url)
                    self.ws_manager.mark_connected(socket_key)
                    connected += 1
                except Exception:
                    self.ws_manager.mark_disconnected(socket_key)
                    disconnected += 1
                    continue

                for idx, row in enumerate(rows):
                    payload_row = row if isinstance(row, dict) else {"raw": row}
                    events.append(
                        StreamIngestionEvent(
                            event_id=self._event_id(now, venue, channel, idx, payload_row),
                            timestamp=now,
                            venue=str(venue),
                            channel=channel,
                            url=url,
                            payload=payload_row,
                        )
                    )
                    counts[channel] += 1

        self.store.append_many(events)
        return {
            "timestamp": now,
            "events_path": str(self.store.events_path),
            "events_written": len(events),
            "market_events": int(counts["market"]),
            "order_events": int(counts["order"]),
            "fill_events": int(counts["fill"]),
            "connected_streams": int(connected),
            "disconnected_streams": int(disconnected),
        }

    async def run_loop(self, *, cycles: int, sleep_seconds: float = 1.0) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for _ in range(max(int(cycles), 0)):
            out.append(await self.collect_once())
            if float(sleep_seconds) > 0:
                await asyncio.sleep(float(sleep_seconds))
        return out
