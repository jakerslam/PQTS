"""AlterEgo toolkit contracts: fast-action intents, recorder sync, and guard policies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from core.compaction_primitives import parse_utc_iso as _parse_iso
from core.compaction_primitives import utc_now_iso as _utc_now_iso


@dataclass(frozen=True)
class FastActionIntentReceipt:
    intent_id: str
    trigger_source: str
    router_gate_passed: bool
    risk_gate_passed: bool
    disposition: str
    reason_codes: Tuple[str, ...]
    emitted_at: str


@dataclass(frozen=True)
class RecorderSourcePoint:
    source_id: str
    source_kind: str
    sequence: int
    timestamp_ms: int


@dataclass(frozen=True)
class RecorderSyncArtifact:
    timeline_id: str
    points: Tuple[RecorderSourcePoint, ...]
    drift_ms: int
    quality_ok: bool
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class NearCloseGuardDecision:
    action: str
    allow_entry: bool
    expectancy_bucket: str
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class WalletSegment:
    segment_id: str
    market_id: str
    action: str
    quantity_delta: float
    provenance_confidence: float
    advisory_only: bool


@dataclass(frozen=True)
class IndicatorProviderManifest:
    provider_id: str
    entitlement_scope: str
    latency_ms: int
    update_cadence_seconds: int
    failure_modes: Tuple[str, ...]
    cost_model: str


@dataclass(frozen=True)
class IndicatorFeedDecision:
    action: str
    freshness_ms: int
    reason_codes: Tuple[str, ...]
    ablation_lift_bps: float


def build_fast_action_intent_receipt(
    *,
    intent_id: str,
    trigger_source: str,
    router_gate_passed: bool,
    risk_gate_passed: bool,
    bypass_attempted: bool,
) -> FastActionIntentReceipt:
    reasons: List[str] = []
    disposition = "submitted"
    if bypass_attempted:
        reasons.append("bypass_attempt_blocked")
        disposition = "blocked"
    elif not bool(router_gate_passed):
        reasons.append("router_gate_block")
        disposition = "blocked"
    elif not bool(risk_gate_passed):
        reasons.append("risk_gate_block")
        disposition = "hold"
    return FastActionIntentReceipt(
        intent_id=str(intent_id).strip(),
        trigger_source=str(trigger_source).strip(),
        router_gate_passed=bool(router_gate_passed),
        risk_gate_passed=bool(risk_gate_passed),
        disposition=disposition,
        reason_codes=tuple(sorted(set(reasons))),
        emitted_at=_utc_now_iso(),
    )


def build_recorder_sync_artifact(
    *,
    timeline_id: str,
    points: List[RecorderSourcePoint],
    max_drift_ms: int,
) -> RecorderSyncArtifact:
    if not points:
        return RecorderSyncArtifact(
            timeline_id=str(timeline_id).strip(),
            points=(),
            drift_ms=0,
            quality_ok=False,
            reason_codes=("no_points",),
        )
    timestamps = [int(row.timestamp_ms) for row in points]
    drift_ms = int(max(timestamps) - min(timestamps))
    reasons: List[str] = []
    if drift_ms > int(max_drift_ms):
        reasons.append("sync_drift_exceeded")
    seq_pairs = [(row.source_id, row.sequence) for row in points]
    if len(seq_pairs) != len(set(seq_pairs)):
        reasons.append("duplicate_source_sequence")
    return RecorderSyncArtifact(
        timeline_id=str(timeline_id).strip(),
        points=tuple(points),
        drift_ms=drift_ms,
        quality_ok=not bool(reasons),
        reason_codes=tuple(sorted(set(reasons))),
    )


def evaluate_near_close_guard(
    *,
    now_ts: str,
    close_ts: str,
    stale_price_age_ms: int,
    estimated_impact_bps: float,
    settlement_uncertainty: float,
    max_entry_window_seconds: int,
    max_stale_price_age_ms: int,
    max_impact_bps: float,
    max_settlement_uncertainty: float,
) -> NearCloseGuardDecision:
    now = _parse_iso(now_ts)
    close = _parse_iso(close_ts)
    seconds_to_close = (close - now).total_seconds()
    reasons: List[str] = []

    if seconds_to_close < 0:
        reasons.append("already_closed")
    if seconds_to_close > int(max_entry_window_seconds):
        reasons.append("outside_close_window")
    if int(stale_price_age_ms) > int(max_stale_price_age_ms):
        reasons.append("stale_price_age_exceeded")
    if float(estimated_impact_bps) > float(max_impact_bps):
        reasons.append("impact_exceeded")
    if float(settlement_uncertainty) > float(max_settlement_uncertainty):
        reasons.append("settlement_uncertainty_exceeded")

    action = "allow"
    if reasons:
        action = "block"
    expectancy_bucket = "close_window" if 0 <= seconds_to_close <= int(max_entry_window_seconds) else "non_close"
    return NearCloseGuardDecision(
        action=action,
        allow_entry=not bool(reasons),
        expectancy_bucket=expectancy_bucket,
        reason_codes=tuple(sorted(set(reasons))),
    )


def segment_wallet_history(events: List[Dict[str, Any]]) -> Tuple[WalletSegment, ...]:
    """Normalize wallet events into accumulation/deaccumulation segments."""

    out: List[WalletSegment] = []
    for idx, row in enumerate(events):
        qty_delta = float(row.get("quantity_delta", 0.0))
        action = "accumulation" if qty_delta >= 0.0 else "deaccumulation"
        confidence = float(row.get("provenance_confidence", 1.0))
        if confidence < 0.0:
            confidence = 0.0
        if confidence > 1.0:
            confidence = 1.0
        out.append(
            WalletSegment(
                segment_id=f"seg_{idx}",
                market_id=str(row.get("market_id", "unknown_market")),
                action=action,
                quantity_delta=qty_delta,
                provenance_confidence=confidence,
                advisory_only=True,
            )
        )
    return tuple(out)


def evaluate_indicator_feed(
    *,
    manifest: IndicatorProviderManifest,
    as_of_ts: str,
    now_ts: str,
    max_freshness_ms: int,
    ablation_lift_bps: float,
    min_ablation_lift_bps: float,
) -> IndicatorFeedDecision:
    now = _parse_iso(now_ts)
    as_of = _parse_iso(as_of_ts)
    freshness_ms = int((now - as_of).total_seconds() * 1000.0)
    reasons: List[str] = []
    action = "allow"

    if freshness_ms > int(max_freshness_ms):
        reasons.append("indicator_feed_stale")
        action = "shadow_only"
    if float(ablation_lift_bps) < float(min_ablation_lift_bps):
        reasons.append("ablation_lift_below_threshold")
        if action == "allow":
            action = "review"
    if int(manifest.latency_ms) <= 0 or int(manifest.update_cadence_seconds) <= 0:
        reasons.append("invalid_provider_manifest")
        action = "shadow_only"

    return IndicatorFeedDecision(
        action=action,
        freshness_ms=freshness_ms,
        reason_codes=tuple(sorted(set(reasons))),
        ablation_lift_bps=float(ablation_lift_bps),
    )
