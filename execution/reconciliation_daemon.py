"""Continuous reconciliation daemon with optional auto-halt on mismatch."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

import pandas as pd

from execution.live_ops_controls import PositionDiff, reconcile_positions
from execution.risk_aware_router import RiskAwareRouter


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


@dataclass(frozen=True)
class ReconciliationConfig:
    """Reconciliation policy configuration."""

    tolerance: float = 1e-6
    max_mismatched_symbols: int = 0
    halt_on_mismatch: bool = True
    symbol_aliases: Dict[str, str] = field(default_factory=dict)


class ReconciliationDaemon:
    """Continuously reconcile internal positions against venue state."""

    def __init__(
        self,
        *,
        router: RiskAwareRouter,
        config: ReconciliationConfig | None = None,
        incident_log_path: str = "data/analytics/reconciliation_incidents.jsonl",
        venue_positions_provider: Optional[
            Callable[[], Awaitable[Dict[str, Dict[str, float]]]]
        ] = None,
    ):
        self.router = router
        self.config = config or ReconciliationConfig()
        self.incident_log_path = Path(incident_log_path)
        self.incident_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.venue_positions_provider = venue_positions_provider

    def _canonical_symbol(self, symbol: str) -> str:
        token = str(symbol).strip()
        if not token:
            return token
        return str(self.config.symbol_aliases.get(token, token))

    def _internal_positions_from_tca(self) -> Dict[str, float]:
        frame = self.router.tca_db.as_dataframe()
        if frame.empty:
            return {}

        frame = frame.copy()
        frame["side"] = frame["side"].astype(str).str.lower()
        frame["signed_qty"] = pd.to_numeric(frame["quantity"], errors="coerce").fillna(0.0)
        frame.loc[frame["side"] == "sell", "signed_qty"] *= -1.0
        grouped = frame.groupby("symbol", as_index=False)["signed_qty"].sum()

        out: Dict[str, float] = {}
        for _, row in grouped.iterrows():
            symbol = self._canonical_symbol(str(row["symbol"]))
            qty = float(row["signed_qty"])
            if abs(qty) <= 1e-12:
                continue
            out[symbol] = out.get(symbol, 0.0) + qty
        return out

    @staticmethod
    def _extract_list_positions(rows: List[Dict[str, Any]]) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            symbol = (
                row.get("symbol")
                or row.get("instrument")
                or row.get("currency")
                or row.get("asset")
                or ""
            )
            qty = (
                row.get("qty")
                or row.get("quantity")
                or row.get("currentUnits")
                or row.get("units")
                or row.get("initialUnits")
                or row.get("balance")
                or row.get("available")
                or row.get("free")
            )
            symbol_token = str(symbol).strip()
            qty_val = _safe_float(qty, 0.0)
            if not symbol_token or abs(qty_val) <= 1e-12:
                continue
            out[symbol_token] = out.get(symbol_token, 0.0) + qty_val
        return out

    async def _adapter_positions(self, adapter: Any) -> Dict[str, float]:
        if adapter is None:
            return {}
        try:
            if hasattr(adapter, "get_positions"):
                rows = await adapter.get_positions()
                if isinstance(rows, list):
                    return self._extract_list_positions(rows)
            if hasattr(adapter, "get_trades"):
                rows = await adapter.get_trades()
                if isinstance(rows, list):
                    return self._extract_list_positions(rows)
            if hasattr(adapter, "get_account_info"):
                payload = await adapter.get_account_info()
                balances = []
                if isinstance(payload, dict):
                    balances = payload.get("balances", []) or []
                if isinstance(balances, list):
                    return self._extract_list_positions(balances)
            if hasattr(adapter, "get_accounts"):
                rows = await adapter.get_accounts()
                if isinstance(rows, list):
                    return self._extract_list_positions(rows)
        except Exception:
            return {}
        return {}

    async def _collect_venue_positions(self) -> Dict[str, Dict[str, float]]:
        if self.venue_positions_provider is not None:
            payload = await self.venue_positions_provider()
            cleaned: Dict[str, Dict[str, float]] = {}
            for venue, mapping in dict(payload or {}).items():
                cleaned[str(venue)] = {
                    self._canonical_symbol(symbol): float(qty)
                    for symbol, qty in dict(mapping or {}).items()
                    if abs(float(qty)) > 1e-12
                }
            return cleaned

        out: Dict[str, Dict[str, float]] = {}
        for venue_name, venue_client in self.router.market_venues.items():
            adapter = venue_client.adapter
            if adapter is None or not venue_client.connected:
                out[str(venue_name)] = {}
                continue

            raw = await self._adapter_positions(adapter)
            out[str(venue_name)] = {
                self._canonical_symbol(symbol): float(qty)
                for symbol, qty in raw.items()
                if abs(float(qty)) > 1e-12
            }
        return out

    @staticmethod
    def _aggregate_venue_positions(
        venue_positions: Dict[str, Dict[str, float]],
    ) -> Dict[str, float]:
        aggregate: Dict[str, float] = {}
        for mapping in venue_positions.values():
            for symbol, qty in mapping.items():
                aggregate[symbol] = aggregate.get(symbol, 0.0) + float(qty)
        return aggregate

    @staticmethod
    def _serialize_diffs(rows: List[PositionDiff]) -> List[Dict[str, Any]]:
        return [asdict(row) for row in rows]

    def _append_incident(self, payload: Dict[str, Any]) -> None:
        with self.incident_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    async def reconcile_once(self) -> Dict[str, Any]:
        internal = self._internal_positions_from_tca()
        venue_positions = await self._collect_venue_positions()
        aggregate_venue = self._aggregate_venue_positions(venue_positions)

        diffs = reconcile_positions(
            internal_positions=internal,
            venue_positions=aggregate_venue,
            tolerance=float(self.config.tolerance),
        )
        mismatches = [row for row in diffs if not row.within_tolerance]
        mismatch_rows = self._serialize_diffs(mismatches)
        auto_halt = False
        halt_reason = ""

        if bool(self.config.halt_on_mismatch) and len(mismatches) > int(
            self.config.max_mismatched_symbols
        ):
            halt_reason = (
                "RECONCILIATION_MISMATCH: "
                f"{len(mismatches)} symbols beyond tolerance {self.config.tolerance}"
            )
            self.router.force_halt(halt_reason)
            auto_halt = True

        payload = {
            "timestamp": _utc_now_iso(),
            "summary": {
                "symbols_checked": len(diffs),
                "mismatches": len(mismatches),
                "halted": bool(self.router.risk_engine.is_halted),
                "auto_halt_triggered": auto_halt,
            },
            "policy": asdict(self.config),
            "internal_positions": internal,
            "venue_positions": venue_positions,
            "aggregate_venue_positions": aggregate_venue,
            "mismatches": mismatch_rows,
            "halt_reason": halt_reason,
        }
        if mismatches:
            self._append_incident(payload)
        return payload

    async def run_loop(
        self,
        *,
        cycles: int,
        sleep_seconds: float = 5.0,
        stop_on_halt: bool = True,
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for _ in range(max(int(cycles), 0)):
            row = await self.reconcile_once()
            out.append(row)
            if bool(stop_on_halt) and bool(row["summary"]["auto_halt_triggered"]):
                break
            if float(sleep_seconds) > 0:
                await asyncio.sleep(float(sleep_seconds))
        return out
