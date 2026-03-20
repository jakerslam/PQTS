"""External multi-repo stack compatibility and bridge-integrity contracts (SLS)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from core.compaction_primitives import parse_utc_iso as _parse_iso


@dataclass(frozen=True)
class StackComponent:
    component_id: str
    layer: str
    version: str
    schema_version: str
    capabilities: Tuple[str, ...]


@dataclass(frozen=True)
class StackCompatibilityDecision:
    compatible: bool
    reason_codes: Tuple[str, ...]
    environment_fingerprint: str


@dataclass(frozen=True)
class FieldVerification:
    field_name: str
    verification_status: str
    confidence: float


@dataclass(frozen=True)
class DatasetVerificationDecision:
    allow_for_execution: bool
    verification_coverage: float
    trust_composition: Dict[str, float]
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class UnderlyingBridgeDecision:
    allow_trade: bool
    mapped_market_id: str
    bridge_confidence: float
    bridge_latency_ms: int
    delay_adjusted_edge_bps: float
    reason_codes: Tuple[str, ...]


def evaluate_stack_compatibility(
    *,
    components: List[StackComponent],
    required_layers: Tuple[str, ...],
    required_capabilities: Dict[str, Tuple[str, ...]],
) -> StackCompatibilityDecision:
    by_layer = {row.layer: row for row in components}
    reasons: List[str] = []

    for layer in required_layers:
        if layer not in by_layer:
            reasons.append(f"missing_layer:{layer}")
            continue
        expected_caps = required_capabilities.get(layer, ())
        seen_caps = set(by_layer[layer].capabilities)
        for cap in expected_caps:
            if cap not in seen_caps:
                reasons.append(f"missing_capability:{layer}:{cap}")

    # Schema drift check: all components must agree on major schema family.
    schema_roots = {row.schema_version.split(".", maxsplit=1)[0] for row in components}
    if len(schema_roots) > 1:
        reasons.append("schema_drift_detected")

    environment_fingerprint = "|".join(
        sorted(f"{row.layer}:{row.component_id}:{row.version}:{row.schema_version}" for row in components)
    )
    return StackCompatibilityDecision(
        compatible=not bool(reasons),
        reason_codes=tuple(sorted(set(reasons))),
        environment_fingerprint=environment_fingerprint,
    )


def evaluate_dataset_verification(
    *,
    fields: List[FieldVerification],
    min_verified_coverage: float,
    min_confidence: float,
) -> DatasetVerificationDecision:
    if not fields:
        return DatasetVerificationDecision(
            allow_for_execution=False,
            verification_coverage=0.0,
            trust_composition={},
            reason_codes=("no_fields",),
        )

    statuses = {"verified": 0, "unverified": 0, "stale": 0}
    verified = 0
    reasons: List[str] = []
    for field in fields:
        status = str(field.verification_status).strip().lower() or "unverified"
        statuses[status] = statuses.get(status, 0) + 1
        if status == "verified" and float(field.confidence) >= float(min_confidence):
            verified += 1
        else:
            reasons.append(f"field_not_verified:{field.field_name}")

    coverage = float(verified) / float(len(fields))
    if coverage < float(min_verified_coverage):
        reasons.append("verification_coverage_below_threshold")

    trust_composition = {key: float(value) / float(len(fields)) for key, value in statuses.items() if value > 0}
    return DatasetVerificationDecision(
        allow_for_execution=not bool(reasons),
        verification_coverage=coverage,
        trust_composition=trust_composition,
        reason_codes=tuple(sorted(set(reasons))),
    )


def evaluate_underlying_contract_bridge(
    *,
    mapped_market_id: str,
    bridge_confidence: float,
    bridge_as_of_ts: str,
    now_ts: str,
    max_bridge_age_ms: int,
    max_bridge_latency_ms: int,
    bridge_latency_ms: int,
    underlying_edge_bps: float,
    translation_uncertainty_bps: float,
    min_delay_adjusted_edge_bps: float,
) -> UnderlyingBridgeDecision:
    as_of = _parse_iso(bridge_as_of_ts)
    now = _parse_iso(now_ts)
    age_ms = int((now - as_of).total_seconds() * 1000.0)
    adjusted_edge = float(underlying_edge_bps) - float(translation_uncertainty_bps)

    reasons: List[str] = []
    if float(bridge_confidence) < 0.0 or float(bridge_confidence) > 1.0:
        reasons.append("bridge_confidence_invalid")
    if float(bridge_confidence) < 0.6:
        reasons.append("bridge_confidence_low")
    if age_ms > int(max_bridge_age_ms):
        reasons.append("bridge_stale")
    if int(bridge_latency_ms) > int(max_bridge_latency_ms):
        reasons.append("bridge_latency_exceeded")
    if adjusted_edge < float(min_delay_adjusted_edge_bps):
        reasons.append("delay_adjusted_edge_below_threshold")

    return UnderlyingBridgeDecision(
        allow_trade=not bool(reasons),
        mapped_market_id=str(mapped_market_id).strip(),
        bridge_confidence=float(bridge_confidence),
        bridge_latency_ms=int(bridge_latency_ms),
        delay_adjusted_edge_bps=float(adjusted_edge),
        reason_codes=tuple(sorted(set(reasons))),
    )
