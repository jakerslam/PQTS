"""Swarm-vs-market mismatch governance contracts (PNSH)."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, sqrt
from statistics import mean, pstdev
from typing import Dict, Tuple

from core.compaction_primitives import parse_utc_iso as _parse_iso


@dataclass(frozen=True)
class SwarmStabilityDecision:
    allow_trade: bool
    central_estimate: float
    dispersion: float
    confidence_low: float
    confidence_high: float
    stability_verdict: str
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class NewsShockResimulationArtifact:
    shock_ts: str
    ingest_ts: str
    recompute_ts: str
    probability_shift: float
    recompute_latency_ms: int
    action: str
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class AttentionTierClassification:
    tier: str
    mismatch_threshold_bps: float
    size_cap_multiplier: float
    min_confidence: float
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class MismatchDecayDecision:
    allow_execute: bool
    projected_mismatch: float
    projected_net_edge_bps: float
    half_life_seconds: float
    reason_codes: Tuple[str, ...]


def evaluate_multi_seed_stability(
    *,
    probabilities_by_seed: Dict[str, float],
    max_dispersion: float,
    min_seed_count: int,
    max_ci_half_width: float,
) -> SwarmStabilityDecision:
    if len(probabilities_by_seed) < int(min_seed_count):
        return SwarmStabilityDecision(
            allow_trade=False,
            central_estimate=0.0,
            dispersion=1.0,
            confidence_low=0.0,
            confidence_high=1.0,
            stability_verdict="fail_closed",
            reason_codes=("insufficient_seed_runs",),
        )

    values = [float(v) for v in probabilities_by_seed.values()]
    central = float(mean(values))
    dispersion = float(pstdev(values)) if len(values) > 1 else 0.0
    ci_half = 1.96 * (dispersion / max(sqrt(len(values)), 1e-9))
    low = max(0.0, central - ci_half)
    high = min(1.0, central + ci_half)

    reasons = []
    if dispersion > float(max_dispersion):
        reasons.append("seed_dispersion_exceeded")
    if ci_half > float(max_ci_half_width):
        reasons.append("confidence_interval_too_wide")

    return SwarmStabilityDecision(
        allow_trade=not bool(reasons),
        central_estimate=central,
        dispersion=dispersion,
        confidence_low=float(low),
        confidence_high=float(high),
        stability_verdict="stable" if not reasons else "fail_closed",
        reason_codes=tuple(sorted(set(reasons))),
    )


def build_news_shock_resimulation_artifact(
    *,
    shock_ts: str,
    ingest_ts: str,
    recompute_ts: str,
    prior_probability: float,
    updated_probability: float,
    max_recompute_latency_ms: int,
) -> NewsShockResimulationArtifact:
    shock = _parse_iso(shock_ts)
    ingest = _parse_iso(ingest_ts)
    recompute = _parse_iso(recompute_ts)
    latency_ms = int((recompute - ingest).total_seconds() * 1000.0)
    reasons = []
    action = "allow"
    if latency_ms > int(max_recompute_latency_ms):
        reasons.append("resimulation_latency_exceeded")
        action = "shadow_only"
    if ingest < shock:
        reasons.append("ingest_before_shock")
        action = "hold"

    return NewsShockResimulationArtifact(
        shock_ts=shock.isoformat(),
        ingest_ts=ingest.isoformat(),
        recompute_ts=recompute.isoformat(),
        probability_shift=float(updated_probability) - float(prior_probability),
        recompute_latency_ms=latency_ms,
        action=action,
        reason_codes=tuple(sorted(set(reasons))),
    )


def classify_attention_tier(
    *,
    participants_24h: int,
    volume_24h_usd: float,
    update_rate_per_minute: float,
    high_attention_participants: int = 2_000,
    high_attention_volume_usd: float = 2_000_000.0,
    medium_attention_participants: int = 300,
    medium_attention_volume_usd: float = 250_000.0,
) -> AttentionTierClassification:
    participants = int(max(participants_24h, 0))
    volume = float(max(volume_24h_usd, 0.0))
    updates = float(max(update_rate_per_minute, 0.0))

    reasons = []
    if participants >= int(high_attention_participants) or volume >= float(high_attention_volume_usd):
        tier = "high_attention"
        threshold = 45.0
        cap = 0.35
        confidence = 0.8
    elif participants >= int(medium_attention_participants) or volume >= float(medium_attention_volume_usd):
        tier = "medium_attention"
        threshold = 30.0
        cap = 0.55
        confidence = 0.7
    else:
        tier = "low_attention"
        threshold = 20.0
        cap = 1.0
        confidence = 0.6
        reasons.append("edge_concentrated_low_attention")

    if updates <= 0.0:
        reasons.append("missing_market_update_rate")

    return AttentionTierClassification(
        tier=tier,
        mismatch_threshold_bps=float(threshold),
        size_cap_multiplier=float(cap),
        min_confidence=float(confidence),
        reason_codes=tuple(sorted(set(reasons))),
    )


def evaluate_mismatch_decay(
    *,
    initial_mismatch: float,
    elapsed_seconds: float,
    half_life_seconds: float,
    projected_cost_bps: float,
    min_post_cost_edge_bps: float,
) -> MismatchDecayDecision:
    half_life = max(float(half_life_seconds), 1.0)
    decay_factor = exp(-0.69314718056 * (max(float(elapsed_seconds), 0.0) / half_life))
    projected = float(initial_mismatch) * decay_factor
    projected_net_edge_bps = (projected * 10_000.0) - float(projected_cost_bps)
    reasons = []
    if projected_net_edge_bps < float(min_post_cost_edge_bps):
        reasons.append("delay_adjusted_edge_below_threshold")
    if projected <= 0.0:
        reasons.append("mismatch_fully_decayed")

    return MismatchDecayDecision(
        allow_execute=not bool(reasons),
        projected_mismatch=float(projected),
        projected_net_edge_bps=float(projected_net_edge_bps),
        half_life_seconds=float(half_life),
        reason_codes=tuple(sorted(set(reasons))),
    )
