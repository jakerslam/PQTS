"""Copy-follow identity resolution and restart-safe event watermarking."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core.compaction_primitives import parse_utc_iso as _parse_iso
from core.compaction_primitives import utc_now_iso as _utc_now_iso


@dataclass(frozen=True)
class IdentityResolutionRecord:
    """Stable mapping from profile handle to execution identity."""

    handle: str
    execution_identity: str
    evidence_source: str
    resolved_at: str
    confidence: float
    valid_until: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "handle": self.handle,
            "execution_identity": self.execution_identity,
            "evidence_source": self.evidence_source,
            "resolved_at": self.resolved_at,
            "confidence": float(self.confidence),
            "valid_until": self.valid_until,
        }

    def __post_init__(self) -> None:
        if not str(self.handle).strip():
            raise ValueError("handle is required")
        if not str(self.execution_identity).strip():
            raise ValueError("execution_identity is required")
        if not str(self.evidence_source).strip():
            raise ValueError("evidence_source is required")
        if not str(self.resolved_at).strip():
            raise ValueError("resolved_at is required")
        if not str(self.valid_until).strip():
            raise ValueError("valid_until is required")
        confidence = float(self.confidence)
        if confidence < 0.0 or confidence > 1.0:
            raise ValueError("confidence must be in [0, 1]")


class CopyFollowIdentityResolver:
    """Resolve and track handle->identity mappings with ambiguity + drift checks."""

    def __init__(self, *, ambiguity_margin: float = 0.05, min_confidence: float = 0.65) -> None:
        self.ambiguity_margin = float(max(0.0, ambiguity_margin))
        self.min_confidence = float(max(0.0, min(min_confidence, 1.0)))
        self._active: dict[str, IdentityResolutionRecord] = {}

    def resolve(
        self,
        *,
        handle: str,
        candidates: list[tuple[str, float]],
        evidence_source: str,
        resolved_at: str | None = None,
        validity_window_seconds: int = 3600,
    ) -> IdentityResolutionRecord:
        norm_handle = str(handle).strip().lower()
        if not norm_handle:
            raise ValueError("handle is required")
        if not candidates:
            raise ValueError("at least one resolution candidate is required")
        clean = sorted(
            [
                (str(identity).strip().lower(), float(conf))
                for identity, conf in candidates
                if str(identity).strip()
            ],
            key=lambda row: row[1],
            reverse=True,
        )
        if not clean:
            raise ValueError("resolution candidates are empty after normalization")

        best_identity, best_confidence = clean[0]
        if best_confidence < self.min_confidence:
            raise RuntimeError("resolution confidence below minimum threshold")
        if len(clean) > 1 and (best_confidence - clean[1][1]) <= self.ambiguity_margin:
            raise RuntimeError("ambiguous profile-to-identity resolution")

        now_ts = str(resolved_at or _utc_now_iso())
        expiry = _parse_iso(now_ts) + timedelta(seconds=max(int(validity_window_seconds), 1))
        record = IdentityResolutionRecord(
            handle=norm_handle,
            execution_identity=best_identity,
            evidence_source=str(evidence_source).strip(),
            resolved_at=now_ts,
            confidence=float(best_confidence),
            valid_until=expiry.isoformat(),
        )
        self._active[norm_handle] = record
        return record

    def get_active(self, handle: str) -> IdentityResolutionRecord | None:
        token = str(handle).strip().lower()
        if not token:
            return None
        return self._active.get(token)

    def require_stable_identity(
        self,
        *,
        handle: str,
        proposed_identity: str,
        now_ts: str | None = None,
        allow_reapproval: bool = False,
    ) -> tuple[bool, str]:
        token = str(handle).strip().lower()
        if token not in self._active:
            return False, "identity_not_resolved"
        record = self._active[token]
        now_dt = _parse_iso(str(now_ts or _utc_now_iso()))
        if now_dt > _parse_iso(record.valid_until):
            return False, "identity_resolution_expired"
        normalized = str(proposed_identity).strip().lower()
        if normalized != record.execution_identity:
            return (bool(allow_reapproval), "identity_changed_requires_reapproval")
        return True, "ok"


class CopyEventWatermarkStore:
    """Durable dedupe store to avoid duplicate follow actions across restarts."""

    def __init__(
        self,
        *,
        path: str | Path,
        max_events: int = 20_000,
        max_age_seconds: int = 14 * 24 * 3600,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_events = max(int(max_events), 100)
        self.max_age_seconds = max(int(max_age_seconds), 60)
        self._events: dict[str, str] = {}
        self._integrity_ok = True
        self._integrity_reason = "ok"
        self._load()

    @staticmethod
    def event_key(
        *,
        source_venue: str,
        source_identity: str,
        tx_hash: str,
        asset: str,
        side: str,
        event_timestamp: str,
    ) -> str:
        return "|".join(
            [
                str(source_venue).strip().lower(),
                str(source_identity).strip().lower(),
                str(tx_hash).strip().lower(),
                str(asset).strip().lower(),
                str(side).strip().lower(),
                str(event_timestamp).strip(),
            ]
        )

    def can_trade(self) -> bool:
        return bool(self._integrity_ok)

    def integrity_status(self) -> tuple[bool, str]:
        return bool(self._integrity_ok), str(self._integrity_reason)

    def has_event(self, *, event_key: str) -> bool:
        return str(event_key).strip() in self._events

    def record_event(self, *, event_key: str, recorded_at: str | None = None) -> None:
        if not self._integrity_ok:
            raise RuntimeError("watermark integrity invalid; shadow/read-only mode required")
        key = str(event_key).strip()
        if not key:
            raise ValueError("event_key is required")
        self._events[key] = str(recorded_at or _utc_now_iso())
        self._prune()
        self._save()

    def _load(self) -> None:
        if not self.path.exists():
            self._events = {}
            self._integrity_ok = True
            self._integrity_reason = "ok"
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            rows = dict(payload.get("events", {}))
            events: dict[str, str] = {}
            for key, ts in rows.items():
                token = str(key).strip()
                if not token:
                    continue
                _ = _parse_iso(str(ts))
                events[token] = str(ts)
            self._events = events
            self._integrity_ok = True
            self._integrity_reason = "ok"
            self._prune()
        except Exception:  # noqa: BLE001
            self._events = {}
            self._integrity_ok = False
            self._integrity_reason = "watermark_state_corrupt"

    def _save(self) -> None:
        payload = {
            "version": 1,
            "updated_at": _utc_now_iso(),
            "events": dict(self._events),
        }
        self.path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    def _prune(self) -> None:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.max_age_seconds)
        keep: list[tuple[str, datetime, str]] = []
        for key, ts in self._events.items():
            ts_dt = _parse_iso(ts)
            if ts_dt >= cutoff:
                keep.append((key, ts_dt, ts))
        keep.sort(key=lambda row: row[1], reverse=True)
        keep = keep[: self.max_events]
        self._events = {key: ts for key, _, ts in keep}
