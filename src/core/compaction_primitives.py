"""Shared small primitives used by compacted contract modules."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """Return ISO-8601 UTC timestamp."""

    return utc_now().isoformat()


def parse_utc_iso(value: str) -> datetime:
    """Parse an ISO timestamp token into timezone-aware UTC."""

    token = str(value).strip()
    if token.endswith("Z"):
        token = token[:-1] + "+00:00"
    dt = datetime.fromisoformat(token)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
