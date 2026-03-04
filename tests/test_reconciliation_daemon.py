"""Tests for reconciliation daemon mismatch detection and auto-halt behavior."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from execution.reconciliation_daemon import ReconciliationConfig, ReconciliationDaemon
from execution.risk_aware_router import RiskAwareRouter
from execution.tca_feedback import TCATradeRecord
from risk.kill_switches import RiskLimits


def _record(*, symbol: str, side: str, qty: float) -> TCATradeRecord:
    return TCATradeRecord(
        trade_id=f"rec_{symbol}_{side}_{qty}",
        timestamp=datetime.now(timezone.utc),
        symbol=symbol,
        exchange="binance",
        side=side,
        quantity=float(qty),
        price=100.0,
        notional=abs(float(qty)) * 100.0,
        predicted_slippage_bps=5.0,
        predicted_commission_bps=1.0,
        predicted_total_bps=6.0,
        realized_slippage_bps=6.0,
        realized_commission_bps=1.0,
        realized_total_bps=7.0,
        spread_bps=2.0,
        vol_24h=1000000.0,
        depth_1pct_usd=50000.0,
    )


def _router(tmp_path: Path) -> RiskAwareRouter:
    router = RiskAwareRouter(
        risk_config=RiskLimits(),
        broker_config={"enabled": True, "live_execution": False},
        tca_db_path=str(tmp_path / "tca.csv"),
    )
    router.set_capital(100000.0, source="unit_test")
    return router


def test_reconciliation_daemon_auto_halts_when_positions_mismatch(tmp_path):
    router = _router(tmp_path)
    router.tca_db.add_record(_record(symbol="BTC-USD", side="buy", qty=2.0))

    async def provider():
        return {"binance": {"BTC-USD": 0.0}}

    daemon = ReconciliationDaemon(
        router=router,
        config=ReconciliationConfig(
            tolerance=1e-9,
            max_mismatched_symbols=0,
            halt_on_mismatch=True,
        ),
        incident_log_path=str(tmp_path / "reconciliation_incidents.jsonl"),
        venue_positions_provider=provider,
    )

    payload = asyncio.run(daemon.reconcile_once())

    assert payload["summary"]["mismatches"] == 1
    assert payload["summary"]["auto_halt_triggered"] is True
    assert router.risk_engine.is_halted is True
    assert payload["halt_reason"].startswith("RECONCILIATION_MISMATCH")

    incident_rows = daemon.incident_log_path.read_text(encoding="utf-8").splitlines()
    assert len(incident_rows) == 1
    incident = json.loads(incident_rows[0])
    assert incident["summary"]["mismatches"] == 1


def test_reconciliation_daemon_stays_clear_when_positions_match_with_aliases(tmp_path):
    router = _router(tmp_path)
    router.tca_db.add_record(_record(symbol="BTCUSDT", side="buy", qty=2.0))

    async def provider():
        return {"binance": {"BTC-USD": 2.0}}

    daemon = ReconciliationDaemon(
        router=router,
        config=ReconciliationConfig(
            tolerance=1e-9,
            max_mismatched_symbols=0,
            halt_on_mismatch=True,
            symbol_aliases={"BTCUSDT": "BTC-USD"},
        ),
        incident_log_path=str(tmp_path / "reconciliation_incidents.jsonl"),
        venue_positions_provider=provider,
    )

    payload = asyncio.run(daemon.reconcile_once())

    assert payload["summary"]["mismatches"] == 0
    assert payload["summary"]["auto_halt_triggered"] is False
    assert router.risk_engine.is_halted is False
    assert daemon.incident_log_path.exists() is False
