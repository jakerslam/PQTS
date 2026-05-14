"""Tests for gap replay and stale-feed failover in market-data resilience."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from execution.market_data_resilience import (  # noqa: E402
    MarketDataResilienceManager,
    MarketDataResiliencePolicy,
)
from execution.risk_aware_router import RiskAwareRouter, VenueClient  # noqa: E402
from risk.kill_switches import RiskLimits  # noqa: E402


def _quote(price: float, ts: datetime) -> Dict[str, Any]:
    return {
        "price": float(price),
        "spread": 0.0002,
        "volume_24h": 1_000_000.0,
        "timestamp": ts.isoformat(),
        "order_book": {
            "bids": [(float(price) * 0.9999, 10.0)],
            "asks": [(float(price) * 1.0001, 10.0)],
        },
    }


def _quote_with_book(price: float, ts: datetime, *, bid: float, ask: float) -> Dict[str, Any]:
    quote = _quote(price, ts)
    quote["bid"] = float(bid)
    quote["ask"] = float(ask)
    quote["order_book"] = {
        "bids": [(float(bid), 10.0)],
        "asks": [(float(ask), 10.0)],
    }
    quote["spread"] = abs(float(ask) - float(bid)) / max(float(price), 1e-12)
    return quote


def test_resilience_manager_uses_backup_venue_when_primary_stale():
    now = datetime(2026, 3, 4, tzinfo=timezone.utc)
    manager = MarketDataResilienceManager(
        policy=MarketDataResiliencePolicy(
            enabled=True,
            stale_after_seconds=1.0,
            replay_window_seconds=60.0,
            backup_venues_by_venue={"binance": ["coinbase"]},
        )
    )
    raw_quotes: Dict[Tuple[str, str], Optional[Dict[str, Any]]] = {
        ("binance", "BTCUSDT"): _quote(100.0, now - timedelta(seconds=5)),
        ("coinbase", "BTCUSDT"): _quote(101.0, now),
    }
    quote, resolution = manager.resolve(
        venue="binance",
        symbol="BTCUSDT",
        market="crypto",
        live_quote=raw_quotes[("binance", "BTCUSDT")],
        raw_quotes=raw_quotes,
        now=now,
    )

    assert quote is not None
    assert quote["price"] == 101.0
    assert resolution.mode == "failover"
    assert resolution.source_venue == "coinbase"


def test_resilience_manager_replays_last_good_quote_on_gap():
    now = datetime(2026, 3, 4, tzinfo=timezone.utc)
    manager = MarketDataResilienceManager(
        policy=MarketDataResiliencePolicy(
            enabled=True,
            stale_after_seconds=1.0,
            replay_window_seconds=60.0,
        )
    )
    live = _quote(200.0, now)
    manager.resolve(
        venue="binance",
        symbol="ETHUSDT",
        market="crypto",
        live_quote=live,
        raw_quotes={("binance", "ETHUSDT"): live},
        now=now,
    )
    replay_quote, replay_resolution = manager.resolve(
        venue="binance",
        symbol="ETHUSDT",
        market="crypto",
        live_quote=None,
        raw_quotes={("binance", "ETHUSDT"): None},
        now=now + timedelta(seconds=10),
    )

    assert replay_quote is not None
    assert replay_quote["price"] == 200.0
    assert replay_quote["replayed"] is True
    assert replay_resolution.mode == "replay"


def test_resilience_manager_rejects_price_sanity_breach_and_replays_last_good():
    now = datetime(2026, 3, 4, tzinfo=timezone.utc)
    manager = MarketDataResilienceManager(
        policy=MarketDataResiliencePolicy(
            enabled=True,
            stale_after_seconds=1.0,
            replay_window_seconds=60.0,
            min_price_by_symbol={"BTC-USD": 10_000.0},
            max_price_by_symbol={"BTC-USD": 500_000.0},
            max_price_deviation_bps=2_000.0,
        )
    )
    live = _quote(75_000.0, now)
    manager.resolve(
        venue="coinbase",
        symbol="BTC-USD",
        market="crypto",
        live_quote=live,
        raw_quotes={("coinbase", "BTC-USD"): live},
        now=now,
    )

    bad = _quote(128.0, now + timedelta(seconds=10))
    replay_quote, replay_resolution = manager.resolve(
        venue="coinbase",
        symbol="BTC-USD",
        market="crypto",
        live_quote=bad,
        raw_quotes={("coinbase", "BTC-USD"): bad},
        now=now + timedelta(seconds=10),
    )

    assert replay_quote is not None
    assert replay_quote["price"] == 75_000.0
    assert replay_quote["replayed"] is True
    assert replay_resolution.mode == "replay"
    metrics = manager.snapshot_metrics()["metrics"]
    assert metrics["sanity_reject_quotes"] == 1


def test_resilience_manager_rejects_midpoint_mismatch():
    now = datetime(2026, 3, 4, tzinfo=timezone.utc)
    manager = MarketDataResilienceManager(
        policy=MarketDataResiliencePolicy(
            enabled=True,
            replay_window_seconds=60.0,
            max_mid_deviation_bps=100.0,
        )
    )
    good = _quote_with_book(100.0, now, bid=99.9, ask=100.1)
    manager.resolve(
        venue="coinbase",
        symbol="TEST-USD",
        market="crypto",
        live_quote=good,
        raw_quotes={("coinbase", "TEST-USD"): good},
        now=now,
    )

    bad = _quote_with_book(130.0, now + timedelta(seconds=1), bid=99.9, ask=100.1)
    quote, resolution = manager.resolve(
        venue="coinbase",
        symbol="TEST-USD",
        market="crypto",
        live_quote=bad,
        raw_quotes={("coinbase", "TEST-USD"): bad},
        now=now + timedelta(seconds=1),
    )

    assert quote is not None
    assert quote["price"] == 100.0
    assert resolution.mode == "replay"
    assert manager.snapshot_metrics()["metrics"]["sanity_reject_quotes"] == 1


def test_resilience_manager_rejects_rolling_price_outlier():
    now = datetime(2026, 3, 4, tzinfo=timezone.utc)
    manager = MarketDataResilienceManager(
        policy=MarketDataResiliencePolicy(
            enabled=True,
            replay_window_seconds=60.0,
            rolling_window_size=5,
            min_rolling_samples=3,
            max_rolling_price_deviation_bps=500.0,
        )
    )
    for idx, price in enumerate([100.0, 101.0, 99.5]):
        quote = _quote(price, now + timedelta(seconds=idx))
        manager.resolve(
            venue="coinbase",
            symbol="TEST-USD",
            market="crypto",
            live_quote=quote,
            raw_quotes={("coinbase", "TEST-USD"): quote},
            now=now + timedelta(seconds=idx),
        )

    outlier = _quote(150.0, now + timedelta(seconds=5))
    quote, resolution = manager.resolve(
        venue="coinbase",
        symbol="TEST-USD",
        market="crypto",
        live_quote=outlier,
        raw_quotes={("coinbase", "TEST-USD"): outlier},
        now=now + timedelta(seconds=5),
    )

    assert quote is not None
    assert quote["price"] == 99.5
    assert resolution.mode == "replay"
    assert manager.snapshot_metrics()["metrics"]["sanity_reject_quotes"] == 1


def test_router_snapshot_failsover_primary_stale_feed_to_backup(tmp_path):
    router = RiskAwareRouter(
        risk_config=RiskLimits(),
        broker_config={
            "enabled": True,
            "market_data_resilience": {
                "enabled": True,
                "stale_after_seconds": 1.0,
                "replay_window_seconds": 60.0,
                "backup_venues_by_venue": {"binance": ["coinbase"]},
            },
        },
        tca_db_path=str(tmp_path / "tca.csv"),
    )
    router.market_venues = {
        "binance": VenueClient(
            market="crypto",
            venue="binance",
            symbols=["BTCUSDT"],
            adapter=object(),
            connected=True,
            is_stub=False,
        ),
        "coinbase": VenueClient(
            market="crypto",
            venue="coinbase",
            symbols=["BTCUSDT"],
            adapter=object(),
            connected=True,
            is_stub=False,
        ),
    }

    now = datetime.now(timezone.utc)
    stale = _quote(100.0, now - timedelta(seconds=5))
    fresh = _quote(101.0, now)

    async def fake_fetch(venue: VenueClient, symbol: str) -> Optional[Dict[str, Any]]:
        _ = symbol
        if venue.venue == "binance":
            return stale
        return fresh

    router._fetch_symbol_quote = fake_fetch  # type: ignore[method-assign]
    snapshot = asyncio.run(router.fetch_market_snapshot())

    assert snapshot["binance"]["BTCUSDT"]["price"] == 101.0
    decisions = snapshot.get("resilience", {}).get("decisions", [])
    modes = {
        (row.get("venue"), row.get("symbol")): row.get("mode")
        for row in decisions
        if isinstance(row, dict)
    }
    assert modes.get(("binance", "BTCUSDT")) == "failover"


def test_router_snapshot_omits_unresolved_quote_when_synthetic_disabled(tmp_path):
    router = RiskAwareRouter(
        risk_config=RiskLimits(),
        broker_config={
            "enabled": True,
            "market_data_resilience": {
                "enabled": True,
                "stale_after_seconds": 1.0,
                "replay_window_seconds": 60.0,
                "allow_synthetic_fallback": False,
            },
        },
        tca_db_path=str(tmp_path / "tca.csv"),
    )
    router.market_venues = {
        "coinbase": VenueClient(
            market="crypto",
            venue="coinbase",
            symbols=["BTC-USD"],
            adapter=object(),
            connected=True,
            is_stub=False,
        ),
    }

    async def fake_fetch(venue: VenueClient, symbol: str) -> Optional[Dict[str, Any]]:
        _ = (venue, symbol)
        return None

    router._fetch_symbol_quote = fake_fetch  # type: ignore[method-assign]
    snapshot = asyncio.run(router.fetch_market_snapshot())

    assert "coinbase" not in snapshot
    assert snapshot["last_price"] == 0.0
    assert snapshot["vol_24h"] == 0.0
    decisions = snapshot.get("resilience", {}).get("decisions", [])
    assert decisions[0]["mode"] == "unresolved"
