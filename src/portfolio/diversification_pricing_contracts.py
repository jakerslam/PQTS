"""Pricing-cohort and diversification-governance contracts (AJO, ZNM)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.compaction_primitives import utc_now_iso as _utc_now_iso


@dataclass(frozen=True)
class BestsellerFloorDecision:
    allowed: bool
    ratio: float
    reason_code: str
    audit_artifact: dict[str, Any]


@dataclass(frozen=True)
class CohortQuality:
    cohort_id: str
    entry_price_tier: str
    retention_30d: float
    retention_60d: float
    retention_90d: float
    upgrade_conversion: float
    support_burden_rate: float
    live_eligibility_attainment: float


@dataclass(frozen=True)
class CohortQualityDecision:
    warning: bool
    reason_codes: tuple[str, ...]
    dominant_cohort_id: str | None


@dataclass(frozen=True)
class DiscountGuardrailDecision:
    allowed: bool
    auto_disabled: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class DiversificationAdmissionDecision:
    allow_admission: bool
    reason_codes: tuple[str, ...]
    marginal_diversification_score: float


@dataclass(frozen=True)
class RedundancyCompressionDecision:
    redundant_clusters: tuple[tuple[str, ...], ...]
    recommended_actions: tuple[str, ...]


def enforce_bestseller_price_floor(
    *,
    bestseller_price: float,
    median_paid_price: float,
    min_bestseller_ratio: float,
    operator_id: str,
    workspace_id: str,
    override_justification: str | None = None,
) -> BestsellerFloorDecision:
    ratio = float(bestseller_price) / max(float(median_paid_price), 1e-9)
    allowed = ratio >= float(min_bestseller_ratio) or bool(override_justification)
    reason = "ok" if allowed else "bestseller_ratio_below_floor"
    artifact = {
        "workspace_id": str(workspace_id).strip(),
        "operator_id": str(operator_id).strip(),
        "timestamp": _utc_now_iso(),
        "override_justification": str(override_justification or "").strip(),
        "ratio": ratio,
    }
    return BestsellerFloorDecision(
        allowed=allowed,
        ratio=ratio,
        reason_code=reason,
        audit_artifact=artifact,
    )


def evaluate_customer_fit_cohort_quality(
    cohorts: list[CohortQuality],
    *,
    min_retention_90d: float,
    min_upgrade_conversion: float,
    max_support_burden_rate: float,
    min_live_eligibility_attainment: float,
) -> CohortQualityDecision:
    if not cohorts:
        return CohortQualityDecision(
            warning=True,
            reason_codes=("no_cohort_data",),
            dominant_cohort_id=None,
        )
    dominant = max(cohorts, key=lambda row: row.retention_30d)
    reasons: list[str] = []
    if dominant.retention_90d < float(min_retention_90d):
        reasons.append("dominant_cohort_retention_weak")
    if dominant.upgrade_conversion < float(min_upgrade_conversion):
        reasons.append("dominant_cohort_upgrade_weak")
    if dominant.support_burden_rate > float(max_support_burden_rate):
        reasons.append("dominant_cohort_support_burden_high")
    if dominant.live_eligibility_attainment < float(min_live_eligibility_attainment):
        reasons.append("dominant_cohort_live_eligibility_low")
    return CohortQualityDecision(
        warning=bool(reasons),
        reason_codes=tuple(sorted(set(reasons))),
        dominant_cohort_id=dominant.cohort_id,
    )


def enforce_discount_entry_offer_guardrail(
    *,
    entry_price: float,
    policy_floor_price: float,
    has_success_criteria: bool,
    has_auto_expiry: bool,
    post_campaign_cohort_quality_ok: bool,
) -> DiscountGuardrailDecision:
    reasons: list[str] = []
    if float(entry_price) < float(policy_floor_price):
        if not has_success_criteria:
            reasons.append("missing_campaign_success_criteria")
        if not has_auto_expiry:
            reasons.append("missing_campaign_auto_expiry")
        if not post_campaign_cohort_quality_ok:
            reasons.append("post_campaign_cohort_quality_below_policy")
    return DiscountGuardrailDecision(
        allowed=not bool(reasons),
        auto_disabled=bool(reasons and not post_campaign_cohort_quality_ok),
        reason_codes=tuple(sorted(set(reasons))),
    )


def evaluate_marginal_diversification_admission(
    *,
    standalone_expectancy: float,
    standalone_risk_score: float,
    mean_correlation_to_active: float,
    expected_portfolio_impact: float,
    max_correlation_threshold: float = 0.80,
    min_portfolio_impact: float = 0.0,
) -> DiversificationAdmissionDecision:
    reasons: list[str] = []
    if float(mean_correlation_to_active) > float(max_correlation_threshold):
        reasons.append("high_correlation_to_active_portfolio")
    if float(expected_portfolio_impact) <= float(min_portfolio_impact):
        reasons.append("marginal_portfolio_impact_non_positive")
    marginal_score = (
        float(standalone_expectancy)
        - float(standalone_risk_score)
        - max(float(mean_correlation_to_active) - 0.5, 0.0)
    )
    return DiversificationAdmissionDecision(
        allow_admission=not bool(reasons),
        reason_codes=tuple(sorted(set(reasons))),
        marginal_diversification_score=marginal_score,
    )


def detect_redundant_strategy_compression(
    *,
    correlation_matrix: dict[tuple[str, str], float],
    active_strategies: set[str],
    redundancy_threshold: float = 0.85,
) -> RedundancyCompressionDecision:
    clusters: list[tuple[str, ...]] = []
    actions: list[str] = []
    processed: set[str] = set()
    for left in sorted(active_strategies):
        if left in processed:
            continue
        cluster = {left}
        for right in sorted(active_strategies):
            if left == right:
                continue
            corr = float(
                correlation_matrix.get((left, right), correlation_matrix.get((right, left), 0.0))
            )
            if corr >= float(redundancy_threshold):
                cluster.add(right)
        if len(cluster) > 1:
            ordered = tuple(sorted(cluster))
            clusters.append(ordered)
            actions.append(f"compress_cluster:{','.join(ordered)}")
            processed.update(cluster)
    return RedundancyCompressionDecision(
        redundant_clusters=tuple(clusters),
        recommended_actions=tuple(actions),
    )
