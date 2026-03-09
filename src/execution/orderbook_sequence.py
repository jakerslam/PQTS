"""Orderbook sequence-gap detection with deterministic recovery workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class SequenceEvent:
    stream_id: str
    expected_sequence: int
    received_sequence: int
    mode: str
    gap_size: int
    recovered: bool
    snapshot_sequence: int | None
    timestamp: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OrderBookSequenceTracker:
    """Track per-stream sequence integrity and perform deterministic recovery."""

    def __init__(self, *, allow_auto_recover: bool = True) -> None:
        self.allow_auto_recover = bool(allow_auto_recover)
        self._expected_next: dict[str, int] = {}
        self._gap_open: dict[str, bool] = {}

    def expected_next(self, stream_id: str) -> int | None:
        return self._expected_next.get(str(stream_id))

    def apply_snapshot(self, *, stream_id: str, snapshot_sequence: int) -> SequenceEvent:
        key = str(stream_id)
        next_seq = int(snapshot_sequence) + 1
        self._expected_next[key] = next_seq
        self._gap_open[key] = False
        return SequenceEvent(
            stream_id=key,
            expected_sequence=next_seq,
            received_sequence=int(snapshot_sequence),
            mode="snapshot_sync",
            gap_size=0,
            recovered=True,
            snapshot_sequence=int(snapshot_sequence),
            timestamp=_utc_now_iso(),
            metadata={},
        )

    def process_update(
        self,
        *,
        stream_id: str,
        sequence: int,
        snapshot_sequence: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SequenceEvent:
        key = str(stream_id)
        seq = int(sequence)
        expected = self._expected_next.get(key)
        info = dict(metadata or {})

        if expected is None:
            self._expected_next[key] = seq + 1
            self._gap_open[key] = False
            return SequenceEvent(
                stream_id=key,
                expected_sequence=seq + 1,
                received_sequence=seq,
                mode="seed",
                gap_size=0,
                recovered=False,
                snapshot_sequence=None,
                timestamp=_utc_now_iso(),
                metadata=info,
            )

        if seq < expected:
            return SequenceEvent(
                stream_id=key,
                expected_sequence=expected,
                received_sequence=seq,
                mode="stale_drop",
                gap_size=0,
                recovered=False,
                snapshot_sequence=None,
                timestamp=_utc_now_iso(),
                metadata=info,
            )

        if seq == expected:
            self._expected_next[key] = seq + 1
            self._gap_open[key] = False
            return SequenceEvent(
                stream_id=key,
                expected_sequence=expected,
                received_sequence=seq,
                mode="in_order",
                gap_size=0,
                recovered=False,
                snapshot_sequence=None,
                timestamp=_utc_now_iso(),
                metadata=info,
            )

        gap_size = seq - expected
        self._gap_open[key] = True
        recovered = False
        mode = "gap_detected"
        snap_seq: int | None = None
        if self.allow_auto_recover and snapshot_sequence is not None:
            snap_seq = int(snapshot_sequence)
            self._expected_next[key] = snap_seq + 1
            self._gap_open[key] = False
            recovered = True
            mode = "gap_recovered_snapshot"

        return SequenceEvent(
            stream_id=key,
            expected_sequence=expected,
            received_sequence=seq,
            mode=mode,
            gap_size=gap_size,
            recovered=recovered,
            snapshot_sequence=snap_seq,
            timestamp=_utc_now_iso(),
            metadata=info,
        )

    def has_open_gap(self, stream_id: str) -> bool:
        return bool(self._gap_open.get(str(stream_id), False))
