"""Read-only external signal-provider adapter with entitlement and schema checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


def _to_epoch_seconds(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    token = str(value or "").strip()
    if not token:
        raise ValueError("missing timestamp")
    if token.endswith("Z"):
        token = token[:-1] + "+00:00"
    return datetime.fromisoformat(token).timestamp()


def _utc_now_seconds() -> float:
    return datetime.now(timezone.utc).timestamp()


_BLOCKED_WRITE_KEYS = {
    "submit_order",
    "place_order",
    "cancel_order",
    "execute_trade",
    "router_action",
}


@dataclass(frozen=True)
class ProviderHealth:
    status: str
    reason_codes: list[str]
    ingestion_age_seconds: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "ingestion_age_seconds": float(self.ingestion_age_seconds),
        }


def validate_provider_signal(
    raw: Mapping[str, Any],
    *,
    required_fields: tuple[str, ...] = ("signal_id", "event_ts", "confidence"),
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    missing = [field for field in required_fields if field not in raw]
    if missing:
        reasons.append(f"missing_fields:{','.join(sorted(missing))}")
    blocked = sorted(key for key in _BLOCKED_WRITE_KEYS if key in raw)
    if blocked:
        reasons.append(f"blocked_write_keys:{','.join(blocked)}")
    return (not reasons), reasons


def normalize_provider_signal(
    raw: Mapping[str, Any],
    *,
    provider: str,
    schema_version: str,
    entitlement_valid: bool,
) -> dict[str, Any]:
    valid, reasons = validate_provider_signal(raw)
    if not valid:
        raise ValueError(";".join(reasons))
    if not entitlement_valid:
        raise ValueError("entitlement_invalid")
    confidence = float(raw.get("confidence", 0.0))
    return {
        "provider": provider,
        "signal_id": str(raw["signal_id"]),
        "event_ts": float(_to_epoch_seconds(raw["event_ts"])),
        "confidence": confidence,
        "schema_version": str(schema_version),
        "entitlement_valid": True,
        "payload": {
            key: value
            for key, value in raw.items()
            if key not in {"signal_id", "event_ts", "confidence"}
        },
        "read_only": True,
    }


def evaluate_provider_health(
    *,
    last_ingest_ts: Any | None,
    entitlement_valid: bool,
    schema_drift_detected: bool,
    now_ts: Any | None = None,
    max_age_seconds: float = 60.0,
) -> ProviderHealth:
    if now_ts is None:
        now_epoch = _utc_now_seconds()
    else:
        now_epoch = _to_epoch_seconds(now_ts)

    reasons: list[str] = []
    if not entitlement_valid:
        reasons.append("entitlement_invalid")
    if schema_drift_detected:
        reasons.append("schema_drift")

    age = 1e9
    if last_ingest_ts is not None:
        age = now_epoch - _to_epoch_seconds(last_ingest_ts)
        if age > max_age_seconds:
            reasons.append("stale_provider_feed")
    else:
        reasons.append("missing_ingest_timestamp")

    if reasons:
        return ProviderHealth(status="degraded", reason_codes=sorted(set(reasons)), ingestion_age_seconds=age)
    return ProviderHealth(status="healthy", reason_codes=[], ingestion_age_seconds=age)
