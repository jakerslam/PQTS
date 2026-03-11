"""Event-intel corroboration and causal-alignment gates for pre-trade validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


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


@dataclass(frozen=True)
class GateDecision:
    allow: bool
    decision: str
    reason_codes: list[str]
    metrics: dict[str, float]

    def as_dict(self) -> dict[str, Any]:
        return {
            "allow": self.allow,
            "decision": self.decision,
            "reason_codes": list(self.reason_codes),
            "metrics": dict(self.metrics),
        }


def evaluate_corroboration(
    records: Sequence[Mapping[str, Any]],
    *,
    min_sources: int = 2,
    max_skew_seconds: float = 120.0,
) -> tuple[bool, str, dict[str, float]]:
    if len(records) < min_sources:
        return False, "insufficient_records", {"record_count": float(len(records))}

    sources: set[str] = set()
    timestamps: list[float] = []
    for record in records:
        source = str(record.get("source", "")).strip().lower()
        if source:
            sources.add(source)
        timestamps.append(_to_epoch_seconds(record.get("event_ts")))
    if len(sources) < min_sources:
        return False, "insufficient_sources", {"source_count": float(len(sources))}
    skew = max(timestamps) - min(timestamps)
    if skew > max_skew_seconds:
        return False, "corroboration_skew_exceeded", {"source_skew_seconds": float(skew)}
    return True, "ok", {"source_count": float(len(sources)), "source_skew_seconds": float(skew)}


def evaluate_causal_alignment(
    *,
    event_ts: Any,
    quote_ts: Any,
    max_clock_skew_seconds: float = 2.0,
) -> tuple[bool, str, dict[str, float]]:
    event_epoch = _to_epoch_seconds(event_ts)
    quote_epoch = _to_epoch_seconds(quote_ts)
    skew = event_epoch - quote_epoch
    if skew > max_clock_skew_seconds:
        return False, "lookahead_violation", {"event_minus_quote_seconds": float(skew)}
    return True, "ok", {"event_minus_quote_seconds": float(skew)}


def evaluate_event_intel_candidate(
    *,
    records: Sequence[Mapping[str, Any]],
    quote_ts: Any,
    now_ts: Any | None = None,
    min_sources: int = 2,
    max_skew_seconds: float = 120.0,
    max_quote_age_seconds: float = 15.0,
    max_event_age_seconds: float = 300.0,
    max_clock_skew_seconds: float = 2.0,
) -> GateDecision:
    now_epoch = _utc_now_seconds() if now_ts is None else _to_epoch_seconds(now_ts)
    quote_epoch = _to_epoch_seconds(quote_ts)
    reason_codes: list[str] = []
    metrics: dict[str, float] = {}

    quote_age = now_epoch - quote_epoch
    metrics["quote_age_seconds"] = float(quote_age)
    if quote_age > max_quote_age_seconds:
        reason_codes.append("stale_quote")

    valid_corr, corr_reason, corr_metrics = evaluate_corroboration(
        records,
        min_sources=min_sources,
        max_skew_seconds=max_skew_seconds,
    )
    metrics.update(corr_metrics)
    if not valid_corr:
        reason_codes.append(corr_reason)

    latest_event = quote_epoch
    for record in records:
        event_epoch = _to_epoch_seconds(record.get("event_ts"))
        latest_event = max(latest_event, event_epoch)
        valid_causal, causal_reason, causal_metrics = evaluate_causal_alignment(
            event_ts=event_epoch,
            quote_ts=quote_epoch,
            max_clock_skew_seconds=max_clock_skew_seconds,
        )
        metrics["max_event_minus_quote_seconds"] = max(
            metrics.get("max_event_minus_quote_seconds", -1e9),
            float(causal_metrics["event_minus_quote_seconds"]),
        )
        if not valid_causal:
            reason_codes.append(causal_reason)

    event_age = now_epoch - latest_event
    metrics["event_age_seconds"] = float(event_age)
    if event_age > max_event_age_seconds:
        reason_codes.append("stale_event")

    deduped = sorted(set(reason_codes))
    allow = not deduped
    return GateDecision(
        allow=allow,
        decision="ALLOW" if allow else "HOLD",
        reason_codes=deduped,
        metrics=metrics,
    )
