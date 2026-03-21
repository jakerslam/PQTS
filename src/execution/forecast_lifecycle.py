"""Forecast artifact lifecycle, revision policy, and resolution-risk gate primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.compaction_primitives import utc_now_iso as _utc_now_iso

_REVISION_CLASSES = {"strengthen", "weaken", "invalidate", "supersede"}
_POSITION_ACTIONS = {"hold", "reduce", "exit", "reprice", "no_trade"}


@dataclass(frozen=True)
class ForecastArtifact:
    """Immutable forecast artifact used for capital-affecting decisions."""

    forecast_id: str
    version: int
    market_id: str
    outcome_id: str
    horizon_end_ts: str
    issued_at: str
    producer_id: str
    workflow_version: str
    estimate_low: float
    estimate_high: float
    evidence_refs: tuple[str, ...]
    supersedes_version: int | None = None
    supersession_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "forecast_id": self.forecast_id,
            "version": self.version,
            "market_id": self.market_id,
            "outcome_id": self.outcome_id,
            "horizon_end_ts": self.horizon_end_ts,
            "issued_at": self.issued_at,
            "producer_id": self.producer_id,
            "workflow_version": self.workflow_version,
            "estimate_low": float(self.estimate_low),
            "estimate_high": float(self.estimate_high),
            "evidence_refs": list(self.evidence_refs),
            "supersedes_version": self.supersedes_version,
            "supersession_reason": self.supersession_reason,
        }

    def __post_init__(self) -> None:
        if not str(self.forecast_id).strip():
            raise ValueError("forecast_id is required")
        if int(self.version) <= 0:
            raise ValueError("version must be >= 1")
        if not str(self.market_id).strip():
            raise ValueError("market_id is required")
        if not str(self.outcome_id).strip():
            raise ValueError("outcome_id is required")
        if not str(self.horizon_end_ts).strip():
            raise ValueError("horizon_end_ts is required")
        if not str(self.issued_at).strip():
            raise ValueError("issued_at is required")
        if not str(self.producer_id).strip():
            raise ValueError("producer_id is required")
        if not str(self.workflow_version).strip():
            raise ValueError("workflow_version is required")
        low = float(self.estimate_low)
        high = float(self.estimate_high)
        if low < 0.0 or high > 1.0 or low > high:
            raise ValueError("estimate range must satisfy 0 <= low <= high <= 1")
        if len(tuple(item for item in self.evidence_refs if str(item).strip())) == 0:
            raise ValueError("evidence_refs must include at least one reference")


@dataclass(frozen=True)
class ForecastRevision:
    forecast_id: str
    from_version: int
    to_version: int
    classification: str
    reason_code: str
    revised_at: str

    def __post_init__(self) -> None:
        token = str(self.classification).strip().lower()
        if token not in _REVISION_CLASSES:
            raise ValueError(f"unsupported revision classification: {self.classification}")


@dataclass(frozen=True)
class ForecastRevisionPolicy:
    """Deterministic action map for material forecast updates on open positions."""

    on_strengthen: str = "hold"
    on_weaken: str = "reduce"
    on_invalidate: str = "exit"
    on_supersede: str = "reprice"

    def __post_init__(self) -> None:
        for action in (
            self.on_strengthen,
            self.on_weaken,
            self.on_invalidate,
            self.on_supersede,
        ):
            if str(action).strip().lower() not in _POSITION_ACTIONS:
                raise ValueError(f"unsupported position action: {action}")


@dataclass(frozen=True)
class ResolutionRiskInputs:
    """Inputs used to score resolution ambiguity and dispute risk."""

    rule_clarity: float
    source_finality: float
    dispute_history_score: float = 0.0
    settlement_caveat_count: int = 0

    def __post_init__(self) -> None:
        for name in ("rule_clarity", "source_finality", "dispute_history_score"):
            value = float(getattr(self, name))
            if value < 0.0 or value > 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if int(self.settlement_caveat_count) < 0:
            raise ValueError("settlement_caveat_count must be >= 0")


@dataclass(frozen=True)
class ResolutionGateDecision:
    allow_entry: bool
    policy_action: str
    ambiguity_score: float
    reason_codes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "allow_entry": bool(self.allow_entry),
            "policy_action": self.policy_action,
            "ambiguity_score": float(self.ambiguity_score),
            "reason_codes": list(self.reason_codes),
        }


class ForecastArtifactRegistry:
    """In-memory registry with immutable artifact versions and decision bindings."""

    def __init__(self) -> None:
        self._artifacts: dict[tuple[str, int], ForecastArtifact] = {}
        self._latest_version: dict[str, int] = {}
        self._decision_bindings: dict[str, tuple[str, int]] = {}
        self._revisions: list[ForecastRevision] = []

    def issue(self, artifact: ForecastArtifact) -> ForecastArtifact:
        key = (artifact.forecast_id, int(artifact.version))
        if key in self._artifacts:
            raise ValueError("forecast artifact version already exists")
        latest = self._latest_version.get(artifact.forecast_id)
        if latest is None and int(artifact.version) != 1:
            raise ValueError("first artifact version must be 1")
        if latest is not None and int(artifact.version) != int(latest) + 1:
            raise ValueError("new artifact version must increment by exactly 1")
        if latest is not None and artifact.supersedes_version != latest:
            raise ValueError("artifact supersedes_version must match latest version")
        self._artifacts[key] = artifact
        self._latest_version[artifact.forecast_id] = int(artifact.version)
        return artifact

    def latest(self, forecast_id: str) -> ForecastArtifact:
        token = str(forecast_id).strip()
        if token not in self._latest_version:
            raise KeyError(f"unknown forecast_id: {forecast_id}")
        version = int(self._latest_version[token])
        return self._artifacts[(token, version)]

    def get(self, forecast_id: str, version: int) -> ForecastArtifact:
        key = (str(forecast_id).strip(), int(version))
        if key not in self._artifacts:
            raise KeyError(f"unknown artifact key: {key}")
        return self._artifacts[key]

    def bind_decision(self, *, decision_id: str, forecast_id: str, version: int) -> None:
        token = str(decision_id).strip()
        if not token:
            raise ValueError("decision_id is required")
        _ = self.get(forecast_id, version)
        self._decision_bindings[token] = (str(forecast_id).strip(), int(version))

    def resolve_decision_binding(self, decision_id: str) -> ForecastArtifact:
        token = str(decision_id).strip()
        if token not in self._decision_bindings:
            raise KeyError(f"unknown decision binding: {decision_id}")
        forecast_id, version = self._decision_bindings[token]
        return self.get(forecast_id, version)

    def revise(
        self,
        *,
        forecast_id: str,
        estimate_low: float,
        estimate_high: float,
        reason_code: str,
        invalidated: bool = False,
        issued_at: str | None = None,
    ) -> tuple[ForecastArtifact, ForecastRevision]:
        previous = self.latest(forecast_id)
        classification = classify_forecast_revision(
            previous,
            estimate_low=estimate_low,
            estimate_high=estimate_high,
            invalidated=invalidated,
        )
        next_version = int(previous.version) + 1
        artifact = ForecastArtifact(
            forecast_id=previous.forecast_id,
            version=next_version,
            market_id=previous.market_id,
            outcome_id=previous.outcome_id,
            horizon_end_ts=previous.horizon_end_ts,
            issued_at=str(issued_at or _utc_now_iso()),
            producer_id=previous.producer_id,
            workflow_version=previous.workflow_version,
            estimate_low=float(estimate_low),
            estimate_high=float(estimate_high),
            evidence_refs=previous.evidence_refs,
            supersedes_version=previous.version,
            supersession_reason=str(reason_code).strip(),
        )
        self.issue(artifact)
        revision = ForecastRevision(
            forecast_id=artifact.forecast_id,
            from_version=previous.version,
            to_version=artifact.version,
            classification=classification,
            reason_code=str(reason_code).strip() or "revision",
            revised_at=artifact.issued_at,
        )
        self._revisions.append(revision)
        return artifact, revision

    def revision_log(self, forecast_id: str | None = None) -> list[ForecastRevision]:
        if forecast_id is None:
            return list(self._revisions)
        token = str(forecast_id).strip()
        return [row for row in self._revisions if row.forecast_id == token]


def classify_forecast_revision(
    previous: ForecastArtifact,
    *,
    estimate_low: float,
    estimate_high: float,
    invalidated: bool = False,
    material_delta: float = 0.05,
) -> str:
    if invalidated:
        return "invalidate"
    low = float(estimate_low)
    high = float(estimate_high)
    if low < 0.0 or high > 1.0 or low > high:
        raise ValueError("revised estimate range must satisfy 0 <= low <= high <= 1")
    current_mid = (float(previous.estimate_low) + float(previous.estimate_high)) / 2.0
    revised_mid = (low + high) / 2.0
    delta = revised_mid - current_mid
    if abs(delta) < float(material_delta):
        return "supersede"
    return "strengthen" if delta > 0.0 else "weaken"


def determine_position_action(
    *,
    revision_classification: str,
    policy: ForecastRevisionPolicy,
) -> str:
    token = str(revision_classification).strip().lower()
    if token not in _REVISION_CLASSES:
        raise ValueError(f"unsupported revision classification: {revision_classification}")
    action_map = {
        "strengthen": policy.on_strengthen,
        "weaken": policy.on_weaken,
        "invalidate": policy.on_invalidate,
        "supersede": policy.on_supersede,
    }
    return str(action_map[token]).strip().lower()


def score_resolution_ambiguity(inputs: ResolutionRiskInputs) -> tuple[float, tuple[str, ...]]:
    clarity_gap = 1.0 - float(inputs.rule_clarity)
    finality_gap = 1.0 - float(inputs.source_finality)
    dispute = float(inputs.dispute_history_score)
    caveat_term = min(float(inputs.settlement_caveat_count) / 5.0, 1.0)

    score = (
        (0.45 * clarity_gap)
        + (0.35 * finality_gap)
        + (0.15 * dispute)
        + (0.05 * caveat_term)
    )

    reasons: list[str] = []
    if clarity_gap >= 0.35:
        reasons.append("resolution_rule_ambiguity_elevated")
    if finality_gap >= 0.30:
        reasons.append("source_finality_weak")
    if dispute >= 0.40:
        reasons.append("historical_dispute_risk_elevated")
    if caveat_term >= 0.40:
        reasons.append("settlement_caveat_density_elevated")
    return float(max(0.0, min(score, 1.0))), tuple(sorted(set(reasons)))


def evaluate_resolution_gate(
    inputs: ResolutionRiskInputs,
    *,
    block_threshold: float = 0.75,
    shadow_only_threshold: float = 0.60,
    size_downweight_threshold: float = 0.45,
) -> ResolutionGateDecision:
    score, reasons = score_resolution_ambiguity(inputs)
    reason_codes = list(reasons)

    if score >= float(block_threshold):
        reason_codes.append("resolution_ambiguity_blocked")
        return ResolutionGateDecision(
            allow_entry=False,
            policy_action="block",
            ambiguity_score=score,
            reason_codes=tuple(sorted(set(reason_codes))),
        )
    if score >= float(shadow_only_threshold):
        reason_codes.append("resolution_ambiguity_shadow_only")
        return ResolutionGateDecision(
            allow_entry=False,
            policy_action="shadow_only",
            ambiguity_score=score,
            reason_codes=tuple(sorted(set(reason_codes))),
        )
    if score >= float(size_downweight_threshold):
        reason_codes.append("resolution_ambiguity_size_downweight")
        return ResolutionGateDecision(
            allow_entry=True,
            policy_action="size_downweight",
            ambiguity_score=score,
            reason_codes=tuple(sorted(set(reason_codes))),
        )
    return ResolutionGateDecision(
        allow_entry=True,
        policy_action="allow",
        ambiguity_score=score,
        reason_codes=tuple(sorted(set(reason_codes))),
    )


def detect_resolution_state_deterioration(
    *,
    baseline: ResolutionRiskInputs,
    current: ResolutionRiskInputs,
    deterioration_delta: float = 0.15,
) -> tuple[bool, str, dict[str, float]]:
    baseline_score, _ = score_resolution_ambiguity(baseline)
    current_score, _ = score_resolution_ambiguity(current)
    delta = current_score - baseline_score
    if delta >= float(deterioration_delta):
        return True, "resolution_risk_deteriorated", {
            "baseline_score": float(baseline_score),
            "current_score": float(current_score),
            "score_delta": float(delta),
        }
    return False, "stable", {
        "baseline_score": float(baseline_score),
        "current_score": float(current_score),
        "score_delta": float(delta),
    }
