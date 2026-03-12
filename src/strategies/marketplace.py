"""Verified strategy marketplace contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class StrategyListing:
    listing_id: str
    strategy_id: str
    title: str
    version: str
    author: str
    verified_badge: bool
    reputation_score: float
    promotion_stage: str
    trust_label: str
    created_at: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "listing_id": self.listing_id,
            "strategy_id": self.strategy_id,
            "title": self.title,
            "version": self.version,
            "author": self.author,
            "verified_badge": bool(self.verified_badge),
            "reputation_score": float(self.reputation_score),
            "promotion_stage": self.promotion_stage,
            "trust_label": self.trust_label,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "StrategyListing":
        listing_id = str(payload.get("listing_id", "")).strip() or f"listing_{abs(hash(str(payload))) % 10_000_000:07d}"
        return cls(
            listing_id=listing_id,
            strategy_id=str(payload.get("strategy_id", "")).strip(),
            title=str(payload.get("title", "")).strip(),
            version=str(payload.get("version", "0.1.0")).strip() or "0.1.0",
            author=str(payload.get("author", "community")).strip() or "community",
            verified_badge=bool(payload.get("verified_badge", False)),
            reputation_score=float(payload.get("reputation_score", 0.0)),
            promotion_stage=str(payload.get("promotion_stage", "paper")).strip() or "paper",
            trust_label=str(payload.get("trust_label", "unverified")).strip() or "unverified",
            created_at=str(payload.get("created_at", _utc_now())),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), Mapping) else {},
        )


def listing_is_verified(row: Mapping[str, Any]) -> bool:
    stage = str(row.get("promotion_stage", "")).strip().lower()
    trust_label = str(row.get("trust_label", "")).strip().lower()
    badge = bool(row.get("verified_badge", False))
    return badge and stage in {"canary", "live"} and trust_label == "reference"


def summarize_marketplace(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    listings = [StrategyListing.from_payload(row) for row in rows]
    verified = [row for row in listings if listing_is_verified(row.to_dict())]
    return {
        "count": len(listings),
        "verified_count": len(verified),
        "listings": [row.to_dict() for row in sorted(listings, key=lambda item: (-item.reputation_score, item.listing_id))],
    }
