"""Competitive dominance closure contracts (DOM family)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from core.compaction_primitives import parse_utc_iso as _parse_iso
from core.compaction_primitives import utc_now as _utc_now
from core.compaction_primitives import utc_now_iso as _utc_now_iso


def _classify_threshold(value: float, good: float, warning: float) -> str:
    if float(value) >= float(good):
        return "green"
    if float(value) >= float(warning):
        return "yellow"
    return "red"


@dataclass(frozen=True)
class CompetitiveDimension:
    name: str
    value: float
    green_threshold: float
    yellow_threshold: float


@dataclass(frozen=True)
class CompetitiveScorecard:
    dimensions: dict[str, str]
    weakest_dimensions: tuple[str, ...]


@dataclass(frozen=True)
class HostedSandboxWorkspace:
    workspace_id: str
    bounded_capital_notional: float
    expires_at: str
    paper_safe_credentials: bool
    no_install_required: bool


@dataclass(frozen=True)
class Tier1VenueCertificationDecision:
    venue: str
    eligible_for_stage: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class RollingProofDensityDecision:
    complete: bool
    missing_cells: tuple[str, ...]


@dataclass(frozen=True)
class DocsTroubleshootingDecision:
    healthy: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class VerifiedExampleDensityDecision:
    meets_density: bool
    verified_count: int
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ConversionReport:
    hosted_conversion: float
    local_conversion: float
    beginner_conversion: float
    professional_conversion: float


@dataclass(frozen=True)
class TrustOpsDashboardPayload:
    release_readiness: str
    benchmark_freshness: str
    venue_certification: str
    docs_freshness: str
    package_availability: str


@dataclass(frozen=True)
class TruthSurfaceGateDecision:
    pass_gate: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ConnectorDepthDecision:
    pass_gate: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class OpsJobReceipt:
    job_id: str
    status: str
    artifacts: tuple[str, ...]
    retries: int
    approval_required: bool


@dataclass(frozen=True)
class CapitalGovernorCard:
    strategy_id: str
    trust_label: str
    promotion_stage: str
    venue_compatibility: tuple[str, ...]
    drawdown_envelope: float
    reject_fill_slippage_score: float
    correlation_budget_score: float
    recommended_capital_budget: float


@dataclass(frozen=True)
class MobileAssistantSafetyDecision:
    allowed: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ScenarioPackCoverageDecision:
    complete: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ReleaseMaturityDecision:
    allowed_transition: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class CasualJourneyDecision:
    valid: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ConstrainedOperatorDecision:
    execute_allowed: bool
    reason_codes: tuple[str, ...]
    memo: str


@dataclass(frozen=True)
class CertifiedPredictionMarketDecision:
    allowed: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class TruthAvailabilityDecision:
    pass_gate: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class CasualConvenienceDecision:
    competitive: bool
    reason_codes: tuple[str, ...]


def build_competitive_scorecard(dimensions: list[CompetitiveDimension]) -> CompetitiveScorecard:
    statuses = {
        row.name: _classify_threshold(row.value, row.green_threshold, row.yellow_threshold)
        for row in dimensions
    }
    weakest = tuple(sorted(k for k, v in statuses.items() if v == "red"))
    return CompetitiveScorecard(dimensions=statuses, weakest_dimensions=weakest)


def create_hosted_sandbox_workspace(
    *,
    workspace_id: str,
    bounded_capital_notional: float,
    ttl_hours: int,
) -> HostedSandboxWorkspace:
    expiry = _utc_now() + timedelta(hours=max(int(ttl_hours), 1))
    return HostedSandboxWorkspace(
        workspace_id=str(workspace_id).strip(),
        bounded_capital_notional=float(bounded_capital_notional),
        expires_at=expiry.isoformat(),
        paper_safe_credentials=True,
        no_install_required=True,
    )


def evaluate_tier1_venue_certification_depth(
    *,
    venue: str,
    has_paper: bool,
    has_canary: bool,
    has_live_readiness: bool,
    has_30d_evidence: bool,
    has_90d_evidence: bool,
) -> Tier1VenueCertificationDecision:
    reasons: list[str] = []
    if not has_paper:
        reasons.append("missing_paper_cert")
    if not has_canary:
        reasons.append("missing_canary_cert")
    if not has_live_readiness:
        reasons.append("missing_live_readiness")
    if not has_30d_evidence or not has_90d_evidence:
        reasons.append("insufficient_rolling_quality_evidence")
    return Tier1VenueCertificationDecision(
        venue=str(venue).strip(),
        eligible_for_stage=not bool(reasons),
        reason_codes=tuple(sorted(set(reasons))),
    )


def evaluate_rolling_proof_density(
    *,
    strategy_count: int,
    venue_count: int,
    regime_count: int,
    monthly_bundle_count: int,
) -> RollingProofDensityDecision:
    required = int(strategy_count) * int(venue_count) * int(regime_count)
    missing: list[str] = []
    if int(monthly_bundle_count) < required:
        missing.append("proof_density_incomplete")
    return RollingProofDensityDecision(complete=not bool(missing), missing_cells=tuple(missing))


def evaluate_docs_troubleshooting_contract(
    *,
    searchable_docs_enabled: bool,
    drift_checks_pass: bool,
    metadata_fresh: bool,
) -> DocsTroubleshootingDecision:
    reasons: list[str] = []
    if not searchable_docs_enabled:
        reasons.append("docs_search_missing")
    if not drift_checks_pass:
        reasons.append("docs_drift_check_failed")
    if not metadata_fresh:
        reasons.append("docs_metadata_stale")
    return DocsTroubleshootingDecision(healthy=not bool(reasons), reason_codes=tuple(reasons))


def evaluate_verified_example_density(
    *,
    verified_example_count: int,
    required_minimum: int = 12,
) -> VerifiedExampleDensityDecision:
    reasons: list[str] = []
    if int(verified_example_count) < int(required_minimum):
        reasons.append("verified_example_density_below_threshold")
    return VerifiedExampleDensityDecision(
        meets_density=not bool(reasons),
        verified_count=int(verified_example_count),
        reason_codes=tuple(reasons),
    )


def build_conversion_report(
    *,
    hosted_conversion: float,
    local_conversion: float,
    beginner_conversion: float,
    professional_conversion: float,
) -> ConversionReport:
    return ConversionReport(
        hosted_conversion=float(hosted_conversion),
        local_conversion=float(local_conversion),
        beginner_conversion=float(beginner_conversion),
        professional_conversion=float(professional_conversion),
    )


def build_trust_ops_dashboard_payload(
    *,
    release_readiness: str,
    benchmark_freshness: str,
    venue_certification: str,
    docs_freshness: str,
    package_availability: str,
) -> TrustOpsDashboardPayload:
    return TrustOpsDashboardPayload(
        release_readiness=release_readiness,
        benchmark_freshness=benchmark_freshness,
        venue_certification=venue_certification,
        docs_freshness=docs_freshness,
        package_availability=package_availability,
    )


def evaluate_truth_surface_gate(
    *,
    readme_ok: bool,
    pypi_ok: bool,
    docs_ok: bool,
    release_notes_ok: bool,
) -> TruthSurfaceGateDecision:
    reasons: list[str] = []
    if not readme_ok:
        reasons.append("readme_surface_missing_or_stale")
    if not pypi_ok:
        reasons.append("pypi_surface_missing_or_stale")
    if not docs_ok:
        reasons.append("docs_surface_missing_or_stale")
    if not release_notes_ok:
        reasons.append("release_notes_surface_missing_or_stale")
    return TruthSurfaceGateDecision(pass_gate=not bool(reasons), reason_codes=tuple(reasons))


def evaluate_connector_certification_depth(
    *,
    connector_status: str,
    paper_ok: bool,
    canary_ok: bool,
    live_ok: bool,
    reliability_budget_ok: bool,
) -> ConnectorDepthDecision:
    status = str(connector_status).strip().lower()
    reasons: list[str] = []
    if status == "beta":
        reasons.append("connector_not_promoted_from_beta")
    if not all([paper_ok, canary_ok, live_ok, reliability_budget_ok]):
        reasons.append("connector_stage_or_budget_requirements_failed")
    return ConnectorDepthDecision(pass_gate=not bool(reasons), reason_codes=tuple(reasons))


def create_ops_job_receipt(
    *,
    job_id: str,
    status: str,
    artifacts: list[str],
    retries: int,
    approval_required: bool,
) -> OpsJobReceipt:
    return OpsJobReceipt(
        job_id=str(job_id).strip(),
        status=str(status).strip().lower(),
        artifacts=tuple(artifacts),
        retries=max(int(retries), 0),
        approval_required=bool(approval_required),
    )


def build_capital_governor_card(
    *,
    strategy_id: str,
    trust_label: str,
    promotion_stage: str,
    venue_compatibility: list[str],
    drawdown_envelope: float,
    reject_fill_slippage_score: float,
    correlation_budget_score: float,
    recommended_capital_budget: float,
) -> CapitalGovernorCard:
    return CapitalGovernorCard(
        strategy_id=str(strategy_id).strip(),
        trust_label=str(trust_label).strip(),
        promotion_stage=str(promotion_stage).strip(),
        venue_compatibility=tuple(venue_compatibility),
        drawdown_envelope=float(drawdown_envelope),
        reject_fill_slippage_score=float(reject_fill_slippage_score),
        correlation_budget_score=float(correlation_budget_score),
        recommended_capital_budget=float(recommended_capital_budget),
    )


def evaluate_mobile_assistant_safety(
    *,
    rbac_ok: bool,
    audit_trail_ok: bool,
    confirmation_required: bool,
    assistant_action_kind: str,
) -> MobileAssistantSafetyDecision:
    reasons: list[str] = []
    token = str(assistant_action_kind).strip().lower()
    if not rbac_ok:
        reasons.append("rbac_failed")
    if not audit_trail_ok:
        reasons.append("audit_trail_missing")
    if token in {"execute", "rollback", "promote"} and not confirmation_required:
        reasons.append("confirmation_required_for_privileged_action")
    return MobileAssistantSafetyDecision(allowed=not bool(reasons), reason_codes=tuple(reasons))


def evaluate_deployment_scenario_pack_coverage(
    *,
    has_fee_regimes: bool,
    has_reconnect_outage: bool,
    has_settlement_oracle_lag: bool,
    has_cross_market_skew: bool,
) -> ScenarioPackCoverageDecision:
    reasons: list[str] = []
    if not has_fee_regimes:
        reasons.append("missing_fee_regime_pack")
    if not has_reconnect_outage:
        reasons.append("missing_reconnect_outage_pack")
    if not has_settlement_oracle_lag:
        reasons.append("missing_settlement_oracle_pack")
    if not has_cross_market_skew:
        reasons.append("missing_cross_market_skew_pack")
    return ScenarioPackCoverageDecision(complete=not bool(reasons), reason_codes=tuple(reasons))


def evaluate_release_maturity_transition(
    *,
    current_state: str,
    target_state: str,
    evidence_pack_present: bool,
    benchmark_ok: bool,
    docs_ok: bool,
) -> ReleaseMaturityDecision:
    order = {"alpha": 1, "beta": 2, "stable": 3}
    cur = str(current_state).strip().lower()
    tgt = str(target_state).strip().lower()
    reasons: list[str] = []
    if tgt not in order or cur not in order or order[tgt] != order[cur] + 1:
        reasons.append("invalid_maturity_transition")
    if not evidence_pack_present:
        reasons.append("missing_evidence_pack")
    if not benchmark_ok:
        reasons.append("benchmark_not_ready")
    if not docs_ok:
        reasons.append("docs_not_ready")
    return ReleaseMaturityDecision(allowed_transition=not bool(reasons), reason_codes=tuple(reasons))


def evaluate_casual_first_journey(
    *,
    primary_screen_count: int,
    advanced_hidden_by_default: bool,
    parity_objects_shared: bool,
) -> CasualJourneyDecision:
    reasons: list[str] = []
    if int(primary_screen_count) > 3:
        reasons.append("casual_path_too_complex")
    if not advanced_hidden_by_default:
        reasons.append("advanced_not_hidden_by_default")
    if not parity_objects_shared:
        reasons.append("casual_pro_parity_broken")
    return CasualJourneyDecision(valid=not bool(reasons), reason_codes=tuple(reasons))


def evaluate_constrained_operator_intelligence(
    *,
    memo_artifact_refs: list[str],
    privileged_execution_requested: bool,
    operator_approved: bool,
) -> ConstrainedOperatorDecision:
    reasons: list[str] = []
    if not memo_artifact_refs:
        reasons.append("missing_evidence_memo_refs")
    if privileged_execution_requested and not operator_approved:
        reasons.append("privileged_execution_requires_approval")
    memo = "Evidence refs:\n" + "\n".join(f"- {x}" for x in memo_artifact_refs)
    return ConstrainedOperatorDecision(
        execute_allowed=not bool(reasons),
        reason_codes=tuple(reasons),
        memo=memo,
    )


def evaluate_certified_prediction_market_scope(
    *,
    market_type: str,
    connector_certified: bool,
    stage: str,
) -> CertifiedPredictionMarketDecision:
    reasons: list[str] = []
    token = str(market_type).strip().lower()
    if token not in {"prediction_market", "forecast_trading"}:
        reasons.append("market_outside_certified_scope")
    if not connector_certified and str(stage).strip().lower() in {"canary", "live"}:
        reasons.append("connector_not_certified_for_stage")
    return CertifiedPredictionMarketDecision(allowed=not bool(reasons), reason_codes=tuple(reasons))


def evaluate_product_truth_availability(
    *,
    readme_links_ok: bool,
    docs_links_ok: bool,
    release_links_ok: bool,
    pypi_links_ok: bool,
    metric_parity_ok: bool,
) -> TruthAvailabilityDecision:
    reasons: list[str] = []
    if not readme_links_ok:
        reasons.append("readme_links_failed")
    if not docs_links_ok:
        reasons.append("docs_links_failed")
    if not release_links_ok:
        reasons.append("release_links_failed")
    if not pypi_links_ok:
        reasons.append("pypi_links_failed")
    if not metric_parity_ok:
        reasons.append("cross_surface_metric_parity_failed")
    return TruthAvailabilityDecision(pass_gate=not bool(reasons), reason_codes=tuple(reasons))


def evaluate_casual_convenience_moat(
    *,
    mobile_notifications_available: bool,
    governed_approval_inbox_available: bool,
    incident_review_mobile_available: bool,
    rbac_audit_ok: bool,
) -> CasualConvenienceDecision:
    reasons: list[str] = []
    if not mobile_notifications_available:
        reasons.append("mobile_notifications_missing")
    if not governed_approval_inbox_available:
        reasons.append("governed_approval_inbox_missing")
    if not incident_review_mobile_available:
        reasons.append("mobile_incident_review_missing")
    if not rbac_audit_ok:
        reasons.append("rbac_or_audit_missing")
    return CasualConvenienceDecision(competitive=not bool(reasons), reason_codes=tuple(reasons))
