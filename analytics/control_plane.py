"""B2B control-plane usage metering and revenue analytics for PQTS SaaS."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass(frozen=True)
class UsageEvent:
    event_id: str
    timestamp: str
    tenant_id: str
    event_type: str
    units: float
    revenue_hint_usd: float
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ControlPlaneMeter:
    """Append-only tenant usage/event meter with deterministic revenue rollups."""

    def __init__(self, log_path: str = "data/analytics/control_plane_usage.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _event_id(
        *, tenant_id: str, event_type: str, timestamp: str, units: float, revenue_hint_usd: float
    ) -> str:
        payload = f"{tenant_id}|{event_type}|{timestamp}|{units:.8f}|{revenue_hint_usd:.8f}"
        token = abs(hash(payload))
        return f"cp_{token:016x}"[:20]

    def emit(
        self,
        *,
        tenant_id: str,
        event_type: str,
        units: float,
        revenue_hint_usd: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> UsageEvent:
        ts = timestamp or self._utc_now_iso()
        event = UsageEvent(
            event_id=self._event_id(
                tenant_id=str(tenant_id),
                event_type=str(event_type),
                timestamp=str(ts),
                units=float(units),
                revenue_hint_usd=float(revenue_hint_usd),
            ),
            timestamp=str(ts),
            tenant_id=str(tenant_id),
            event_type=str(event_type),
            units=float(units),
            revenue_hint_usd=float(revenue_hint_usd),
            metadata=dict(metadata or {}),
        )
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")
        return event

    def read_events(self, *, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.log_path.exists():
            return []

        rows: List[Dict[str, Any]] = []
        with self.log_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                payload = line.strip()
                if not payload:
                    continue
                try:
                    row = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict):
                    continue
                if tenant_id is not None and str(row.get("tenant_id")) != str(tenant_id):
                    continue
                rows.append(row)

        rows.sort(key=lambda row: str(row.get("timestamp", "")))
        return rows

    def usage_summary(self, *, window_days: int = 30) -> Dict[str, Any]:
        rows = self.read_events()
        if not rows:
            return {
                "tenants": [],
                "summary": {
                    "tenant_count": 0,
                    "events": 0,
                    "window_days": int(window_days),
                    "mrr_estimate_usd": 0.0,
                    "arr_estimate_usd": 0.0,
                },
            }

        frame = pd.DataFrame(rows)
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
        frame = frame.dropna(subset=["timestamp"])
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(int(window_days), 1))
        scoped = frame[frame["timestamp"] >= cutoff]
        if scoped.empty:
            return {
                "tenants": [],
                "summary": {
                    "tenant_count": 0,
                    "events": 0,
                    "window_days": int(window_days),
                    "mrr_estimate_usd": 0.0,
                    "arr_estimate_usd": 0.0,
                },
            }

        grouped = (
            scoped.groupby("tenant_id", as_index=False)
            .agg(
                events=("event_id", "count"),
                total_units=("units", "sum"),
                revenue_hint_usd=("revenue_hint_usd", "sum"),
            )
            .sort_values("revenue_hint_usd", ascending=False)
            .reset_index(drop=True)
        )

        tenants = []
        for _, row in grouped.iterrows():
            tenants.append(
                {
                    "tenant_id": str(row["tenant_id"]),
                    "events": int(row["events"]),
                    "total_units": float(row["total_units"]),
                    "revenue_hint_usd": float(row["revenue_hint_usd"]),
                }
            )

        mrr = float(grouped["revenue_hint_usd"].sum())
        return {
            "tenants": tenants,
            "summary": {
                "tenant_count": int(len(tenants)),
                "events": int(len(scoped)),
                "window_days": int(window_days),
                "mrr_estimate_usd": mrr,
                "arr_estimate_usd": mrr * 12.0,
            },
        }


def pricing_tier_recommendation(
    *,
    total_units: float,
    monthly_events: int,
) -> Dict[str, Any]:
    """Deterministic tier recommendation for B2B packaging decisions."""
    units = float(total_units)
    events = int(monthly_events)

    if units >= 100000.0 or events >= 20000:
        tier = "enterprise"
        base_price = 2499.0
    elif units >= 20000.0 or events >= 5000:
        tier = "pro"
        base_price = 999.0
    else:
        tier = "starter"
        base_price = 599.0

    return {
        "tier": tier,
        "base_price_usd": float(base_price),
        "inputs": {
            "total_units": units,
            "monthly_events": events,
        },
    }
