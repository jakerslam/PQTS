"""Provider-quality, flow-confirmation, and tool-surface contracts."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean
from typing import Any

from core.compaction_primitives import utc_now_iso as _utc_now_iso


@dataclass(frozen=True)
class ForecasterPrediction:
    contributor_id: str
    market_segment: str
    forecast_probability: float
    realized_label: int
    forecast_ts: str
    target_definition: str
    horizon: str
    evaluation_delay_ms: int


@dataclass(frozen=True)
class ForecasterQualityScore:
    contributor_id: str
    calibration_error: float
    brier_score: float
    log_loss: float
    coverage: float
    sample_count: int
    score_version: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "contributor_id": self.contributor_id,
            "calibration_error": float(self.calibration_error),
            "brier_score": float(self.brier_score),
            "log_loss": float(self.log_loss),
            "coverage": float(self.coverage),
            "sample_count": int(self.sample_count),
            "score_version": self.score_version,
        }


@dataclass(frozen=True)
class DelayAdjustedProviderDecision:
    action: str
    pre_delay_edge_bps: float
    post_delay_edge_bps: float
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class FeedbackVelocityMetrics:
    market_class: str
    median_time_to_label_hours: float
    episodes_per_day: float
    train_cycle_hours: float
    velocity_score: float


@dataclass(frozen=True)
class AdaptiveBaselineDecision:
    allow_promotion: bool
    lift_over_static_bps: float
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class LiquidationPressurePoint:
    price_band: str
    pressure_magnitude: float
    direction: str
    source_version: str
    captured_at: str


@dataclass(frozen=True)
class FlowConfirmationDecision:
    action: str
    supporting_venues: tuple[str, ...]
    agreement_ratio: float
    rejected_noise_filters: tuple[str, ...]
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class SponsoredClaimRecord:
    claim_id: str
    source_url: str
    sponsored_claim: bool
    trust_label: str
    verification_status: str
    captured_at: str


@dataclass(frozen=True)
class ProbabilityBandAttribution:
    band: str
    sample_count: int
    net_expectancy: float
    drawdown: float
    slippage_bps: float


@dataclass(frozen=True)
class ProbabilityBandDecision:
    allow_promotion: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class TradeCountVolumeIllusionWarning:
    warn: bool
    reason_codes: tuple[str, ...]
    turnover_adjusted_alpha: float
    outcome_concentration: float


@dataclass(frozen=True)
class ReadOnlyToolCapability:
    tool_id: str
    asset_classes: tuple[str, ...]
    fields: tuple[str, ...]
    granularity: str
    entitlement_requirement: str
    freshness_posture: str
    coverage_gaps: tuple[str, ...]
    read_only: bool


@dataclass(frozen=True)
class ToolSurfaceResponse:
    provider_identity: str
    as_of_timestamp: str
    schema_version: str
    permission_scope: str
    payload: dict[str, Any]
    reason_codes: tuple[str, ...]
    ok: bool


def score_external_forecaster(
    predictions: list[ForecasterPrediction],
    *,
    score_version: str = "sams.v1",
) -> ForecasterQualityScore:
    if not predictions:
        raise ValueError("predictions are required")
    contributor_ids = {row.contributor_id for row in predictions}
    if len(contributor_ids) != 1:
        raise ValueError("predictions must belong to one contributor")

    probs = [min(max(float(row.forecast_probability), 1e-6), 1.0 - 1e-6) for row in predictions]
    labels = [1 if int(row.realized_label) else 0 for row in predictions]
    brier = mean([(p - y) ** 2 for p, y in zip(probs, labels)])
    logloss = mean([-(y * math.log(p) + (1 - y) * math.log(1.0 - p)) for p, y in zip(probs, labels)])
    calibration_error = abs(mean(probs) - mean(labels))
    coverage = 1.0
    return ForecasterQualityScore(
        contributor_id=predictions[0].contributor_id,
        calibration_error=calibration_error,
        brier_score=brier,
        log_loss=logloss,
        coverage=coverage,
        sample_count=len(predictions),
        score_version=score_version,
    )


def evaluate_delay_adjusted_provider_consumption(
    *,
    pre_delay_edge_bps: float,
    post_delay_edge_bps: float,
    min_post_delay_edge_bps: float = 2.0,
) -> DelayAdjustedProviderDecision:
    reasons: list[str] = []
    action = "allow"
    if float(post_delay_edge_bps) <= 0.0:
        reasons.append("post_delay_edge_non_positive")
        action = "shadow_only"
    elif float(post_delay_edge_bps) < float(min_post_delay_edge_bps):
        reasons.append("post_delay_edge_below_threshold")
        action = "down_weight"
    if float(post_delay_edge_bps) < float(pre_delay_edge_bps) * 0.25:
        reasons.append("delay_decay_severe")
    return DelayAdjustedProviderDecision(
        action=action,
        pre_delay_edge_bps=float(pre_delay_edge_bps),
        post_delay_edge_bps=float(post_delay_edge_bps),
        reason_codes=tuple(sorted(set(reasons))),
    )


def compute_feedback_velocity_metrics(
    *,
    market_class: str,
    median_time_to_label_hours: float,
    episodes_per_day: float,
    train_cycle_hours: float,
) -> FeedbackVelocityMetrics:
    velocity = float(episodes_per_day) / max(float(train_cycle_hours), 1e-9)
    velocity /= max(float(median_time_to_label_hours), 1e-9)
    return FeedbackVelocityMetrics(
        market_class=str(market_class).strip(),
        median_time_to_label_hours=float(median_time_to_label_hours),
        episodes_per_day=float(episodes_per_day),
        train_cycle_hours=float(train_cycle_hours),
        velocity_score=velocity,
    )


def evaluate_adaptive_vs_static_baseline(
    *,
    adaptive_net_edge_bps: float,
    static_net_edge_bps: float,
    parity_assumptions_ok: bool,
    min_lift_bps: float = 2.0,
) -> AdaptiveBaselineDecision:
    lift = float(adaptive_net_edge_bps) - float(static_net_edge_bps)
    reasons: list[str] = []
    if not parity_assumptions_ok:
        reasons.append("baseline_parity_assumptions_missing")
    if lift < float(min_lift_bps):
        reasons.append("adaptive_lift_below_threshold")
    return AdaptiveBaselineDecision(
        allow_promotion=not bool(reasons),
        lift_over_static_bps=lift,
        reason_codes=tuple(sorted(set(reasons))),
    )


def build_liquidation_pressure_surface(
    points: list[LiquidationPressurePoint],
) -> dict[str, Any]:
    if not points:
        raise ValueError("pressure points are required")
    return {
        "points": [
            {
                "price_band": row.price_band,
                "pressure_magnitude": float(row.pressure_magnitude),
                "direction": row.direction,
                "source_version": row.source_version,
                "captured_at": row.captured_at,
            }
            for row in points
        ]
    }


def evaluate_multi_venue_flow_confirmation(
    *,
    venue_votes: dict[str, bool],
    noise_filters_rejected: list[str],
    min_agreement_ratio: float = 0.6,
) -> FlowConfirmationDecision:
    if not venue_votes:
        return FlowConfirmationDecision(
            action="block",
            supporting_venues=(),
            agreement_ratio=0.0,
            rejected_noise_filters=tuple(noise_filters_rejected),
            reason_codes=("no_venue_confirmation",),
        )
    supporting = tuple(sorted(k for k, v in venue_votes.items() if bool(v)))
    ratio = float(len(supporting)) / float(len(venue_votes))
    reasons: list[str] = []
    action = "allow"
    if ratio < float(min_agreement_ratio):
        reasons.append("cross_venue_confirmation_missing")
        action = "down_rank"
    return FlowConfirmationDecision(
        action=action,
        supporting_venues=supporting,
        agreement_ratio=ratio,
        rejected_noise_filters=tuple(noise_filters_rejected),
        reason_codes=tuple(sorted(set(reasons))),
    )


def ingest_sponsored_claim(
    *,
    claim_id: str,
    source_url: str,
    sponsored_claim: bool,
    verification_status: str = "unverified",
) -> SponsoredClaimRecord:
    status = str(verification_status).strip().lower() or "unverified"
    trust = "sponsored_claim" if sponsored_claim else "unsponsored_claim"
    return SponsoredClaimRecord(
        claim_id=str(claim_id).strip(),
        source_url=str(source_url).strip(),
        sponsored_claim=bool(sponsored_claim),
        trust_label=trust,
        verification_status=status,
        captured_at=_utc_now_iso(),
    )


def evaluate_probability_band_specialization(
    *,
    claimed_bands: set[str],
    observed: list[ProbabilityBandAttribution],
    min_samples_per_band: int,
    min_net_expectancy: float,
) -> ProbabilityBandDecision:
    by_band = {row.band: row for row in observed}
    reasons: list[str] = []
    for band in claimed_bands:
        if band not in by_band:
            reasons.append("claimed_band_missing")
            continue
        row = by_band[band]
        if int(row.sample_count) < int(min_samples_per_band):
            reasons.append("band_sample_too_low")
        if float(row.net_expectancy) < float(min_net_expectancy):
            reasons.append("band_expectancy_below_threshold")
    return ProbabilityBandDecision(
        allow_promotion=not bool(reasons),
        reason_codes=tuple(sorted(set(reasons))),
    )


def detect_trade_count_volume_illusion(
    *,
    turnover_adjusted_alpha: float,
    top_outcome_contribution_ratio: float,
    min_turnover_adjusted_alpha: float = 0.0,
    max_concentration_ratio: float = 0.6,
) -> TradeCountVolumeIllusionWarning:
    reasons: list[str] = []
    if float(turnover_adjusted_alpha) <= float(min_turnover_adjusted_alpha):
        reasons.append("turnover_adjusted_alpha_weak")
    if float(top_outcome_contribution_ratio) > float(max_concentration_ratio):
        reasons.append("outcome_concentration_elevated")
    return TradeCountVolumeIllusionWarning(
        warn=bool(reasons),
        reason_codes=tuple(sorted(set(reasons))),
        turnover_adjusted_alpha=float(turnover_adjusted_alpha),
        outcome_concentration=float(top_outcome_contribution_ratio),
    )


def register_read_only_tool_surface(capability: ReadOnlyToolCapability) -> None:
    if not capability.read_only:
        raise RuntimeError("market-data tool surfaces must remain read-only")


def build_tool_surface_response(
    *,
    provider_identity: str,
    as_of_timestamp: str,
    schema_version: str,
    permission_scope: str,
    payload: dict[str, Any],
    provider_state: str,
    in_declared_coverage: bool,
) -> ToolSurfaceResponse:
    state = str(provider_state).strip().lower()
    reasons: list[str] = []
    if state in {"stale", "degraded", "unauthorized"}:
        reasons.append(f"provider_{state}")
    if not in_declared_coverage:
        reasons.append("provider_outside_declared_coverage")
    return ToolSurfaceResponse(
        provider_identity=str(provider_identity).strip(),
        as_of_timestamp=str(as_of_timestamp).strip(),
        schema_version=str(schema_version).strip(),
        permission_scope=str(permission_scope).strip(),
        payload=(payload if not reasons else {}),
        reason_codes=tuple(sorted(set(reasons))),
        ok=not bool(reasons),
    )


def validate_tool_registry_parity(
    *,
    tool_capability_ids: set[str],
    canonical_connector_ids: set[str],
) -> bool:
    return tool_capability_ids == canonical_connector_ids
