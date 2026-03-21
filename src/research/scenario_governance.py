"""Scenario-governance primitives for provenance, debate, and committee lineage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from core.compaction_primitives import parse_utc_iso as _parse_iso
from core.compaction_primitives import utc_now as _utc_now
from core.compaction_primitives import utc_now_iso as _utc_now_iso


@dataclass(frozen=True)
class SeedMaterial:
    material_id: str
    kind: str
    source_ref: str
    captured_at: str
    trust_label: str
    parser_version: str
    verifiable: bool

    def __post_init__(self) -> None:
        if not str(self.material_id).strip():
            raise ValueError("material_id is required")
        if not str(self.kind).strip():
            raise ValueError("kind is required")
        if not str(self.source_ref).strip():
            raise ValueError("source_ref is required")
        if not str(self.captured_at).strip():
            raise ValueError("captured_at is required")
        if not str(self.trust_label).strip():
            raise ValueError("trust_label is required")
        if not str(self.parser_version).strip():
            raise ValueError("parser_version is required")


@dataclass(frozen=True)
class ScenarioSeedIngestionResult:
    accepted_material_ids: tuple[str, ...]
    rejected_material_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class EntityNode:
    node_id: str
    entity_kind: str
    confidence: float
    source_refs: tuple[str, ...]
    updated_at: str
    conflict_flags: tuple[str, ...]


@dataclass(frozen=True)
class CatalystEdge:
    edge_id: str
    from_node: str
    to_node: str
    relation: str
    confidence: float
    source_refs: tuple[str, ...]
    updated_at: str
    conflict_flags: tuple[str, ...]


@dataclass(frozen=True)
class EntityCatalystGraph:
    nodes: tuple[EntityNode, ...]
    edges: tuple[CatalystEdge, ...]


@dataclass(frozen=True)
class CounterfactualSimulationResult:
    scenario_id: str
    challenger_only: bool
    changed_assumptions: tuple[str, ...]
    affected_entities: tuple[str, ...]
    expected_market_impact: str
    uncertainty_notes: str


@dataclass(frozen=True)
class EvidenceMemo:
    observed_facts: tuple[str, ...]
    inferred_scenarios: tuple[str, ...]
    speculative_counterfactuals: tuple[str, ...]
    artifact_links: tuple[str, ...]
    memo_text: str


@dataclass(frozen=True)
class PopulationArchetypeResult:
    archetype: str
    participation_count: int
    decision_distribution: dict[str, float]
    confidence_low: float
    confidence_high: float


@dataclass(frozen=True)
class PopulationScenarioReport:
    archetypes: tuple[PopulationArchetypeResult, ...]
    challenger_evidence_only: bool


@dataclass(frozen=True)
class ConsensusCascadeTelemetry:
    consensus_concentration: float
    polarization_score: float
    cascade_trigger_score: float
    instability_flag: bool


@dataclass(frozen=True)
class ExternalClaimRecord:
    claim_id: str
    source_url: str
    captured_at: str
    verification_status: str
    trust_label: str
    claim_text: str


@dataclass(frozen=True)
class RolePolicy:
    role: str
    may_read: bool
    may_propose: bool
    may_simulate: bool
    may_request_execute: bool
    may_approve_execute: bool


@dataclass(frozen=True)
class RolePipelinePolicyResult:
    valid: bool
    reason_codes: tuple[str, ...]
    roles: tuple[RolePolicy, ...]


@dataclass(frozen=True)
class AgentHandoffReceipt:
    candidate_id: str
    upstream_receipt_refs: tuple[str, ...]
    from_role: str
    to_role: str
    timestamp: str
    delta_summary: str
    latency_ms: int
    queue_ms: int


@dataclass(frozen=True)
class PrivateDataSource:
    source_ref: str
    entitlement_scope: str
    permitted_use: str
    retention_policy: str
    expires_at: str


@dataclass(frozen=True)
class PrivateDataProvenanceDecision:
    allowed: bool
    reason_codes: tuple[str, ...]
    sources: tuple[str, ...]


@dataclass(frozen=True)
class ScenarioCandidate:
    scenario_id: str
    ranking_score: float
    oos_score: float
    used_post_event_data: bool
    has_verifiable_private_labels: bool


@dataclass(frozen=True)
class ScenarioWinnerDecision:
    allowed: bool
    chosen_scenario_id: str | None
    reason_codes: tuple[str, ...]
    full_candidate_set: tuple[str, ...]
    ranking_objective: str
    oos_window: str


@dataclass(frozen=True)
class DebateResult:
    action: str
    rounds_run: int
    unresolved_score: float
    reason_codes: tuple[str, ...]
    affirmative_case: str
    counter_case: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class CommitteeStage:
    role: str
    input_refs: tuple[str, ...]
    output_summary: str
    timestamp: str
    disposition: str


@dataclass(frozen=True)
class CommitteeDecisionLineage:
    stages: tuple[CommitteeStage, ...]
    reconstructable: bool
    reason_codes: tuple[str, ...]


def ingest_seed_materials(
    materials: list[SeedMaterial],
    *,
    max_age_days: int = 14,
) -> ScenarioSeedIngestionResult:
    """Ingest scenario seed materials and fail closed on stale/unverifiable inputs."""

    accepted: list[str] = []
    rejected: list[str] = []
    reasons: list[str] = []
    cutoff = _utc_now() - timedelta(days=max(int(max_age_days), 1))
    for row in materials:
        if not bool(row.verifiable):
            rejected.append(row.material_id)
            reasons.append("seed_material_unverifiable")
            continue
        if _parse_iso(row.captured_at) < cutoff:
            rejected.append(row.material_id)
            reasons.append("seed_material_stale")
            continue
        accepted.append(row.material_id)
    return ScenarioSeedIngestionResult(
        accepted_material_ids=tuple(sorted(set(accepted))),
        rejected_material_ids=tuple(sorted(set(rejected))),
        reason_codes=tuple(sorted(set(reasons))),
    )


def build_entity_catalyst_graph(
    *,
    nodes: list[EntityNode],
    edges: list[CatalystEdge],
) -> EntityCatalystGraph:
    """Construct machine-readable entity/catalyst graph with provenance metadata."""

    node_ids = {row.node_id for row in nodes}
    if not node_ids:
        raise ValueError("at least one node is required")
    for edge in edges:
        if edge.from_node not in node_ids or edge.to_node not in node_ids:
            raise ValueError("edge references unknown node")
    return EntityCatalystGraph(nodes=tuple(nodes), edges=tuple(edges))


def run_counterfactual_simulation(
    *,
    scenario_id: str,
    changed_assumptions: list[str],
    affected_entities: list[str],
    expected_market_impact: str,
    uncertainty_notes: str,
    challenger_only: bool = True,
) -> CounterfactualSimulationResult:
    """Run scenario-lab simulation as challenger-only evidence."""

    if not bool(challenger_only):
        raise RuntimeError("counterfactual simulations must remain challenger-only")
    if not changed_assumptions:
        raise ValueError("changed_assumptions are required")
    return CounterfactualSimulationResult(
        scenario_id=str(scenario_id).strip(),
        challenger_only=True,
        changed_assumptions=tuple(changed_assumptions),
        affected_entities=tuple(affected_entities),
        expected_market_impact=str(expected_market_impact).strip(),
        uncertainty_notes=str(uncertainty_notes).strip(),
    )


def generate_evidence_memo(
    *,
    observed_facts: list[str],
    inferred_scenarios: list[str],
    speculative_counterfactuals: list[str],
    artifact_links: list[str],
) -> EvidenceMemo:
    """Generate memo with explicit observed/inferred/speculative separation."""

    if not artifact_links:
        raise ValueError("artifact_links are required")
    memo_lines = [
        "Observed facts:",
        *[f"- {row}" for row in observed_facts],
        "Inferred scenarios:",
        *[f"- {row}" for row in inferred_scenarios],
        "Speculative counterfactuals:",
        *[f"- {row}" for row in speculative_counterfactuals],
        "Artifact links:",
        *[f"- {row}" for row in artifact_links],
    ]
    return EvidenceMemo(
        observed_facts=tuple(observed_facts),
        inferred_scenarios=tuple(inferred_scenarios),
        speculative_counterfactuals=tuple(speculative_counterfactuals),
        artifact_links=tuple(artifact_links),
        memo_text="\n".join(memo_lines),
    )


def simulate_heterogeneous_population(
    archetypes: list[PopulationArchetypeResult],
) -> PopulationScenarioReport:
    """Persist per-archetype distributions and keep scenario output challenger-only."""

    if not archetypes:
        raise ValueError("archetypes are required")
    return PopulationScenarioReport(
        archetypes=tuple(archetypes),
        challenger_evidence_only=True,
    )


def compute_consensus_polarization_cascade(
    *,
    decision_distribution: dict[str, float],
    subgroup_bias_scores: list[float],
    cascade_trigger_score: float,
    cascade_threshold: float = 0.65,
) -> ConsensusCascadeTelemetry:
    """Compute consensus/polarization metrics and instability flag."""

    consensus = max((float(v) for v in decision_distribution.values()), default=0.0)
    polarization = max((float(v) for v in subgroup_bias_scores), default=0.0)
    cascade = float(cascade_trigger_score)
    return ConsensusCascadeTelemetry(
        consensus_concentration=consensus,
        polarization_score=polarization,
        cascade_trigger_score=cascade,
        instability_flag=cascade >= float(cascade_threshold),
    )


def ingest_external_claim(
    *,
    claim_id: str,
    source_url: str,
    claim_text: str,
    captured_at: str | None = None,
    verification_status: str = "unverified",
) -> ExternalClaimRecord:
    """Tag extraordinary imported claims as unverified by default."""

    status = str(verification_status).strip().lower() or "unverified"
    trust_label = "unverified_external_claim" if status != "verified" else "verified_external_claim"
    return ExternalClaimRecord(
        claim_id=str(claim_id).strip(),
        source_url=str(source_url).strip(),
        captured_at=str(captured_at or _utc_now_iso()),
        verification_status=status,
        trust_label=trust_label,
        claim_text=str(claim_text).strip(),
    )


def can_claim_affect_promotion(claim: ExternalClaimRecord) -> bool:
    return claim.verification_status == "verified"


def validate_role_segregated_pipeline_policy(
    roles: list[RolePolicy],
) -> RolePipelinePolicyResult:
    """Require role segregation so one role cannot originate and self-approve execution."""

    reasons: list[str] = []
    by_role = {row.role: row for row in roles}
    for row in roles:
        if row.may_propose and row.may_approve_execute:
            reasons.append("self_approval_not_allowed")
    required = {"scanner", "signal_synth", "risk_filter", "execution_intent"}
    missing = sorted(required.difference(by_role.keys()))
    if missing:
        reasons.append("missing_required_roles")
    return RolePipelinePolicyResult(
        valid=not bool(reasons),
        reason_codes=tuple(sorted(set(reasons))),
        roles=tuple(roles),
    )


def emit_agent_handoff_receipt(
    *,
    candidate_id: str,
    upstream_receipt_refs: list[str],
    from_role: str,
    to_role: str,
    delta_summary: str,
    latency_ms: int,
    queue_ms: int,
    timestamp: str | None = None,
) -> AgentHandoffReceipt:
    """Emit stage transition receipt with latency and queue diagnostics."""

    return AgentHandoffReceipt(
        candidate_id=str(candidate_id).strip(),
        upstream_receipt_refs=tuple(upstream_receipt_refs),
        from_role=str(from_role).strip(),
        to_role=str(to_role).strip(),
        timestamp=str(timestamp or _utc_now_iso()),
        delta_summary=str(delta_summary).strip(),
        latency_ms=max(int(latency_ms), 0),
        queue_ms=max(int(queue_ms), 0),
    )


def build_private_data_provenance_decision(
    sources: list[PrivateDataSource],
    *,
    now_ts: str | None = None,
) -> PrivateDataProvenanceDecision:
    """Fail closed when private-data entitlement metadata is missing/expired."""

    now_dt = _parse_iso(str(now_ts or _utc_now_iso()))
    reasons: list[str] = []
    allowed_sources: list[str] = []
    for row in sources:
        if not str(row.entitlement_scope).strip():
            reasons.append("missing_entitlement_scope")
            continue
        if not str(row.permitted_use).strip():
            reasons.append("missing_permitted_use")
            continue
        if now_dt > _parse_iso(row.expires_at):
            reasons.append("entitlement_expired")
            continue
        allowed_sources.append(row.source_ref)
    return PrivateDataProvenanceDecision(
        allowed=not bool(reasons),
        reason_codes=tuple(sorted(set(reasons))),
        sources=tuple(sorted(set(allowed_sources))),
    )


def evaluate_scenario_winner_selection_bias(
    *,
    candidates: list[ScenarioCandidate],
    chosen_scenario_id: str,
    ranking_objective: str,
    oos_window: str,
) -> ScenarioWinnerDecision:
    """Fail closed when winner depends on in-sample leakage or unverifiable labels."""

    if not candidates:
        raise ValueError("candidates are required")
    by_id = {row.scenario_id: row for row in candidates}
    if chosen_scenario_id not in by_id:
        raise ValueError("chosen_scenario_id is not in candidates")
    chosen = by_id[chosen_scenario_id]
    reasons: list[str] = []
    if chosen.used_post_event_data:
        reasons.append("post_event_information_detected")
    if not chosen.has_verifiable_private_labels:
        reasons.append("private_labels_unverifiable")
    top_oos = max(float(row.oos_score) for row in candidates)
    if float(chosen.oos_score) < top_oos:
        reasons.append("winner_not_oos_superior")
    return ScenarioWinnerDecision(
        allowed=not bool(reasons),
        chosen_scenario_id=(chosen_scenario_id if not reasons else None),
        reason_codes=tuple(sorted(set(reasons))),
        full_candidate_set=tuple(sorted(by_id.keys())),
        ranking_objective=str(ranking_objective).strip(),
        oos_window=str(oos_window).strip(),
    )


def run_structured_bull_bear_debate(
    *,
    affirmative_case: str,
    counter_case: str,
    evidence_refs: list[str],
    rounds_run: int,
    unresolved_contradiction_score: float,
    max_unresolved_score: float = 0.40,
    min_rounds: int = 2,
) -> DebateResult:
    """Default to hold/block when contradictions remain unresolved."""

    reasons: list[str] = []
    if int(rounds_run) < int(min_rounds):
        reasons.append("insufficient_debate_rounds")
    if float(unresolved_contradiction_score) > float(max_unresolved_score):
        reasons.append("material_contradictions_unresolved")
    action = "advance" if not reasons else "hold"
    return DebateResult(
        action=action,
        rounds_run=int(rounds_run),
        unresolved_score=float(unresolved_contradiction_score),
        reason_codes=tuple(sorted(set(reasons))),
        affirmative_case=str(affirmative_case).strip(),
        counter_case=str(counter_case).strip(),
        evidence_refs=tuple(evidence_refs),
    )


def build_committee_decision_lineage(
    stages: list[CommitteeStage],
) -> CommitteeDecisionLineage:
    """Build one linked committee chain from analyst through PM verdict."""

    required_roles = {"analyst", "debate", "trader", "risk", "portfolio_manager"}
    present = {str(row.role).strip().lower() for row in stages}
    reasons: list[str] = []
    if required_roles.difference(present):
        reasons.append("missing_committee_stage")
    if any(str(row.disposition).strip().lower() not in {"advance", "revise", "hold", "reject"} for row in stages):
        reasons.append("invalid_stage_disposition")
    return CommitteeDecisionLineage(
        stages=tuple(stages),
        reconstructable=not bool(reasons),
        reason_codes=tuple(sorted(set(reasons))),
    )
