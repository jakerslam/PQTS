"""Venue failover policy for multi-venue execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class VenueHealth:
    venue: str
    latency_ms: float
    reject_rate: float
    connected: bool
    liquidity_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "venue": self.venue,
            "latency_ms": float(self.latency_ms),
            "reject_rate": float(self.reject_rate),
            "connected": bool(self.connected),
            "liquidity_score": float(self.liquidity_score),
        }


def select_primary_and_fallback(
    rows: list[Mapping[str, Any]],
    *,
    max_latency_ms: float = 250.0,
    max_reject_rate: float = 0.20,
) -> dict[str, Any]:
    health_rows: list[VenueHealth] = []
    for row in rows:
        health_rows.append(
            VenueHealth(
                venue=str(row.get("venue", "")).strip(),
                latency_ms=float(row.get("latency_ms", 99999.0)),
                reject_rate=float(row.get("reject_rate", 1.0)),
                connected=bool(row.get("connected", False)),
                liquidity_score=float(row.get("liquidity_score", 0.0)),
            )
        )
    eligible = [
        row
        for row in health_rows
        if row.venue
        and row.connected
        and row.latency_ms <= float(max_latency_ms)
        and row.reject_rate <= float(max_reject_rate)
    ]
    ranked = sorted(
        eligible,
        key=lambda row: (row.reject_rate, row.latency_ms, -row.liquidity_score, row.venue),
    )
    primary = ranked[0] if ranked else None
    fallback = ranked[1] if len(ranked) > 1 else None
    return {
        "primary": primary.to_dict() if primary else None,
        "fallback": fallback.to_dict() if fallback else None,
        "eligible_count": len(ranked),
        "all_rows": [row.to_dict() for row in health_rows],
        "failover_ready": primary is not None and fallback is not None,
    }
