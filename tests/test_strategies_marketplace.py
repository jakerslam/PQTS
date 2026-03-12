"""Tests for strategy marketplace listing contracts."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from strategies.marketplace import listing_is_verified, summarize_marketplace  # noqa: E402


def test_listing_verification_requires_badge_reference_and_canary_or_live() -> None:
    assert listing_is_verified(
        {
            "verified_badge": True,
            "promotion_stage": "canary",
            "trust_label": "reference",
        }
    )
    assert not listing_is_verified(
        {
            "verified_badge": True,
            "promotion_stage": "paper",
            "trust_label": "reference",
        }
    )
    assert not listing_is_verified(
        {
            "verified_badge": True,
            "promotion_stage": "canary",
            "trust_label": "diagnostic_only",
        }
    )


def test_marketplace_summary_ranks_by_reputation() -> None:
    payload = summarize_marketplace(
        [
            {
                "listing_id": "a",
                "strategy_id": "alpha",
                "title": "Alpha",
                "version": "0.1.0",
                "author": "ops",
                "verified_badge": True,
                "reputation_score": 0.7,
                "promotion_stage": "canary",
                "trust_label": "reference",
            },
            {
                "listing_id": "b",
                "strategy_id": "beta",
                "title": "Beta",
                "version": "0.1.0",
                "author": "ops",
                "verified_badge": False,
                "reputation_score": 0.4,
                "promotion_stage": "paper",
                "trust_label": "unverified",
            },
        ]
    )
    assert payload["count"] == 2
    assert payload["verified_count"] == 1
    assert payload["listings"][0]["listing_id"] == "a"
