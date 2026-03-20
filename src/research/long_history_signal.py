"""Long-history cross-asset prior signal governance (ML50 family)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class CoverageRow:
    asset_class: str
    symbol: str
    start_year: int
    end_year: int
    missing_ratio: float


@dataclass(frozen=True)
class CoverageManifest:
    unified_schema_version: str
    coverage_by_asset: Dict[str, Dict[str, int]]
    missingness_profile: Dict[str, float]
    survivorship_policy: str


@dataclass(frozen=True)
class RegimeSplitResult:
    train_years: Tuple[int, ...]
    test_years: Tuple[int, ...]
    leakage_safe: bool
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class EnsembleOutput:
    combined_probability: float
    component_outputs: Dict[str, float]
    component_weights: Dict[str, float]
    confidence_interval: Tuple[float, float]
    fallback_state: str


@dataclass(frozen=True)
class PriorSafetyDecision:
    action: str
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class RecencyDriftDecision:
    action: str
    downweighted_components: Tuple[str, ...]
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class ThroughputBudgetDecision:
    action: str
    market_count: int
    p95_latency_ms: float
    skipped_candidates: int
    reason_codes: Tuple[str, ...]


def build_coverage_manifest(
    *,
    rows: List[CoverageRow],
    schema_version: str,
    survivorship_policy: str,
) -> CoverageManifest:
    coverage: Dict[str, Dict[str, int]] = {}
    missing: Dict[str, float] = {}
    for row in rows:
        token = str(row.asset_class).strip().lower()
        entry = coverage.setdefault(token, {"symbols": 0, "min_year": row.start_year, "max_year": row.end_year})
        entry["symbols"] += 1
        entry["min_year"] = min(int(entry["min_year"]), int(row.start_year))
        entry["max_year"] = max(int(entry["max_year"]), int(row.end_year))
        values = missing.setdefault(token, 0.0)
        missing[token] = float(values) + float(row.missing_ratio)

    missingness_profile = {}
    for asset, entry in coverage.items():
        denom = max(int(entry["symbols"]), 1)
        missingness_profile[asset] = float(missing.get(asset, 0.0)) / float(denom)

    return CoverageManifest(
        unified_schema_version=str(schema_version).strip(),
        coverage_by_asset=coverage,
        missingness_profile=missingness_profile,
        survivorship_policy=str(survivorship_policy).strip(),
    )


def evaluate_walk_forward_split(
    *,
    train_years: List[int],
    test_years: List[int],
    feature_asof_safe: bool,
    leakage_detected: bool,
) -> RegimeSplitResult:
    reasons = []
    if leakage_detected:
        reasons.append("leakage_detected")
    if not feature_asof_safe:
        reasons.append("feature_asof_violation")
    if set(train_years).intersection(set(test_years)):
        reasons.append("overlapping_train_test_windows")
    return RegimeSplitResult(
        train_years=tuple(sorted(set(int(y) for y in train_years))),
        test_years=tuple(sorted(set(int(y) for y in test_years))),
        leakage_safe=not bool(reasons),
        reason_codes=tuple(sorted(set(reasons))),
    )


def combine_domain_models(
    *,
    component_probabilities: Dict[str, float],
    component_weights: Dict[str, float],
    component_confidence: Dict[str, float],
) -> EnsembleOutput:
    if not component_probabilities:
        return EnsembleOutput(
            combined_probability=0.0,
            component_outputs={},
            component_weights={},
            confidence_interval=(0.0, 1.0),
            fallback_state="no_components",
        )

    total_weight = 0.0
    weighted_sum = 0.0
    for key, probability in component_probabilities.items():
        weight = max(float(component_weights.get(key, 0.0)), 0.0)
        weighted_sum += float(probability) * weight
        total_weight += weight
    if total_weight <= 0.0:
        return EnsembleOutput(
            combined_probability=0.0,
            component_outputs=dict(component_probabilities),
            component_weights=dict(component_weights),
            confidence_interval=(0.0, 1.0),
            fallback_state="invalid_weights",
        )

    combined = weighted_sum / total_weight
    avg_conf = sum(max(min(float(component_confidence.get(key, 0.0)), 1.0), 0.0) for key in component_probabilities) / max(
        len(component_probabilities), 1
    )
    width = max(0.02, 0.25 * (1.0 - avg_conf))
    return EnsembleOutput(
        combined_probability=float(max(min(combined, 1.0), 0.0)),
        component_outputs=dict(component_probabilities),
        component_weights=dict(component_weights),
        confidence_interval=(float(max(combined - width, 0.0)), float(min(combined + width, 1.0))),
        fallback_state="ok",
    )


def evaluate_prior_only_safety(
    *,
    prior_signal_supports_trade: bool,
    primary_strategy_supports_trade: bool,
    conflict_action: str,
) -> PriorSafetyDecision:
    if prior_signal_supports_trade and primary_strategy_supports_trade:
        return PriorSafetyDecision(action="allow", reason_codes=())
    if prior_signal_supports_trade and not primary_strategy_supports_trade:
        action = str(conflict_action).strip().lower() or "hold"
        if action not in {"hold", "size_down", "shadow_only"}:
            action = "hold"
        return PriorSafetyDecision(action=action, reason_codes=("prior_primary_conflict",))
    return PriorSafetyDecision(action="hold", reason_codes=("prior_not_supportive",))


def evaluate_recency_drift_controls(
    *,
    drift_by_component: Dict[str, float],
    max_component_drift: float,
    downweight_factor: float,
) -> RecencyDriftDecision:
    downgraded = tuple(
        sorted(
            key
            for key, value in drift_by_component.items()
            if float(value) > float(max_component_drift)
        )
    )
    if not downgraded:
        return RecencyDriftDecision(action="allow", downweighted_components=(), reason_codes=())

    action = "downweight" if float(downweight_factor) < 1.0 else "disable"
    return RecencyDriftDecision(
        action=action,
        downweighted_components=downgraded,
        reason_codes=("component_drift_exceeded",),
    )


def evaluate_throughput_budget(
    *,
    market_count: int,
    p95_latency_ms: float,
    max_latency_ms: float,
    skipped_candidates: int,
    max_skip_ratio: float,
) -> ThroughputBudgetDecision:
    reasons = []
    if float(p95_latency_ms) > float(max_latency_ms):
        reasons.append("latency_budget_exceeded")
    skip_ratio = float(skipped_candidates) / max(float(market_count), 1.0)
    if skip_ratio > float(max_skip_ratio):
        reasons.append("skip_ratio_exceeded")

    action = "allow"
    if reasons:
        action = "degrade_to_shadow"

    return ThroughputBudgetDecision(
        action=action,
        market_count=int(market_count),
        p95_latency_ms=float(p95_latency_ms),
        skipped_candidates=int(skipped_candidates),
        reason_codes=tuple(sorted(set(reasons))),
    )
