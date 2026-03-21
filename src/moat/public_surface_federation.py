"""Public proof/docs federation and release evidence-pack contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from core.compaction_primitives import parse_utc_iso as _parse_iso
from core.compaction_primitives import utc_now as _utc_now
from core.compaction_primitives import utc_now_iso as _utc_now_iso


@dataclass(frozen=True)
class PublicProofBundle:
    bundle_id: str
    release_window: str
    generated_at: str
    benchmark_summary_ref: str
    promotion_stage_summary_ref: str
    external_cohort_summary_ref: str
    venue_certification_summary_ref: str
    links: dict[str, str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "release_window": self.release_window,
            "generated_at": self.generated_at,
            "benchmark_summary_ref": self.benchmark_summary_ref,
            "promotion_stage_summary_ref": self.promotion_stage_summary_ref,
            "external_cohort_summary_ref": self.external_cohort_summary_ref,
            "venue_certification_summary_ref": self.venue_certification_summary_ref,
            "links": dict(self.links),
        }


@dataclass(frozen=True)
class PublicProofFreshnessDecision:
    ready: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class CanonicalReleaseContentBundle:
    bundle_id: str
    readme_snippets: dict[str, str]
    pypi_fragments: dict[str, str]
    docs_landing_content: dict[str, str]
    in_product_help: dict[str, str]


@dataclass(frozen=True)
class DocsSurfaceHealthDecision:
    healthy: bool
    broken_links: tuple[str, ...]
    command_parity_mismatches: tuple[str, ...]
    drift_mismatches: tuple[str, ...]


@dataclass(frozen=True)
class GuidedStudioScreen:
    screen_id: str
    title: str
    explanation: str
    next_action: str
    cli_equivalent: str
    mode: str


@dataclass(frozen=True)
class GuidedStudioFlowDecision:
    valid: bool
    reason_codes: tuple[str, ...]
    primary_screen_count: int


@dataclass(frozen=True)
class PublicReleaseEvidencePack:
    release_tag: str
    generated_at: str
    benchmark_status: str
    docs_link_health: str
    certification_status: str
    external_cohort_status: str
    trust_limitations: tuple[str, ...]
    maturity_state: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "release_tag": self.release_tag,
            "generated_at": self.generated_at,
            "benchmark_status": self.benchmark_status,
            "docs_link_health": self.docs_link_health,
            "certification_status": self.certification_status,
            "external_cohort_status": self.external_cohort_status,
            "trust_limitations": list(self.trust_limitations),
            "maturity_state": self.maturity_state,
        }


def build_public_proof_bundle(
    *,
    release_window: str,
    benchmark_summary_ref: str,
    promotion_stage_summary_ref: str,
    external_cohort_summary_ref: str,
    venue_certification_summary_ref: str,
    docs_landing_link: str,
    trust_dashboard_link: str,
    release_notes_link: str,
) -> PublicProofBundle:
    """Build rolling public proof bundle and links for public surfaces."""

    generated = _utc_now_iso()
    bundle_id = f"proof.{release_window}.{generated}"
    return PublicProofBundle(
        bundle_id=bundle_id,
        release_window=str(release_window).strip(),
        generated_at=generated,
        benchmark_summary_ref=str(benchmark_summary_ref).strip(),
        promotion_stage_summary_ref=str(promotion_stage_summary_ref).strip(),
        external_cohort_summary_ref=str(external_cohort_summary_ref).strip(),
        venue_certification_summary_ref=str(venue_certification_summary_ref).strip(),
        links={
            "docs_landing": str(docs_landing_link).strip(),
            "trust_dashboard": str(trust_dashboard_link).strip(),
            "release_notes": str(release_notes_link).strip(),
        },
    )


def evaluate_public_proof_freshness(
    *,
    bundle: PublicProofBundle | None,
    max_age_hours: int,
    now_ts: str | None = None,
) -> PublicProofFreshnessDecision:
    reasons: list[str] = []
    if bundle is None:
        reasons.append("missing_public_proof_bundle")
        return PublicProofFreshnessDecision(ready=False, reason_codes=tuple(reasons))
    now = _parse_iso(str(now_ts or _utc_now_iso()))
    age = now - _parse_iso(bundle.generated_at)
    if age > timedelta(hours=max(int(max_age_hours), 1)):
        reasons.append("public_proof_bundle_stale")
    return PublicProofFreshnessDecision(ready=not bool(reasons), reason_codes=tuple(reasons))


def build_canonical_release_content_bundle(
    *,
    bundle_id: str,
    readme_snippets: dict[str, str],
    pypi_fragments: dict[str, str],
    docs_landing_content: dict[str, str],
    in_product_help: dict[str, str],
) -> CanonicalReleaseContentBundle:
    """Federate release content from one canonical bundle across all surfaces."""

    return CanonicalReleaseContentBundle(
        bundle_id=str(bundle_id).strip(),
        readme_snippets=dict(readme_snippets),
        pypi_fragments=dict(pypi_fragments),
        docs_landing_content=dict(docs_landing_content),
        in_product_help=dict(in_product_help),
    )


def evaluate_docs_surface_health(
    *,
    link_status: dict[str, int],
    command_pairs: list[tuple[str, str]],
    content_hashes: dict[str, str],
) -> DocsSurfaceHealthDecision:
    """Check broken links, command parity, and cross-surface drift."""

    broken = tuple(sorted(k for k, code in link_status.items() if int(code) >= 400))
    parity: list[str] = []
    for left, right in command_pairs:
        if str(left).strip() != str(right).strip():
            parity.append(f"{left}!={right}")
    drift: list[str] = []
    if len(set(content_hashes.values())) > 1:
        drift = [f"{k}:{v}" for k, v in sorted(content_hashes.items())]
    return DocsSurfaceHealthDecision(
        healthy=not bool(broken or parity or drift),
        broken_links=broken,
        command_parity_mismatches=tuple(sorted(parity)),
        drift_mismatches=tuple(drift),
    )


def validate_guided_studio_first_success_flow(
    *,
    primary_screens: list[GuidedStudioScreen],
    advanced_surfaces_progressively_disclosed: bool,
    max_primary_screens: int = 3,
) -> GuidedStudioFlowDecision:
    reasons: list[str] = []
    if len(primary_screens) > int(max_primary_screens):
        reasons.append("too_many_primary_screens")
    for row in primary_screens:
        if not row.explanation.strip() or not row.next_action.strip() or not row.cli_equivalent.strip():
            reasons.append("missing_human_or_cli_explanation")
            break
    if not advanced_surfaces_progressively_disclosed:
        reasons.append("advanced_surface_not_progressively_disclosed")
    return GuidedStudioFlowDecision(
        valid=not bool(reasons),
        reason_codes=tuple(sorted(set(reasons))),
        primary_screen_count=len(primary_screens),
    )


def build_public_release_evidence_pack(
    *,
    release_tag: str,
    benchmark_status: str,
    docs_link_health: str,
    certification_status: str,
    external_cohort_status: str,
    trust_limitations: list[str],
    maturity_state: str,
) -> PublicReleaseEvidencePack:
    """Build active release evidence pack consumed by release/docs/trust/about surfaces."""

    return PublicReleaseEvidencePack(
        release_tag=str(release_tag).strip(),
        generated_at=_utc_now_iso(),
        benchmark_status=str(benchmark_status).strip(),
        docs_link_health=str(docs_link_health).strip(),
        certification_status=str(certification_status).strip(),
        external_cohort_status=str(external_cohort_status).strip(),
        trust_limitations=tuple(trust_limitations),
        maturity_state=str(maturity_state).strip(),
    )


def allow_public_claim_from_evidence_pack(
    *,
    evidence_pack: PublicReleaseEvidencePack | None,
    claim_kind: str,
) -> bool:
    """Block public readiness/performance/usability claims without active evidence pack."""

    if evidence_pack is None:
        return False
    token = str(claim_kind).strip().lower()
    if token in {"readiness", "performance", "usability"}:
        return True
    return False
