"""Bayesian probability update engine with persisted evidence metadata."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from core.persistence import EventPersistenceStore


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class BayesianState:
    market_id: str
    alpha: float
    beta: float
    prior_probability: float
    posterior_probability: float
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BayesianUpdateRecord:
    market_id: str
    prior_alpha: float
    prior_beta: float
    posterior_alpha: float
    posterior_beta: float
    prior_probability: float
    posterior_probability: float
    evidence_successes: float
    evidence_failures: float
    evidence_weight: float
    evidence_source: str
    evidence_metadata: dict[str, Any]
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BayesianProbabilityEngine:
    """Beta-Bernoulli posterior updater with persistence side effects."""

    def __init__(
        self,
        *,
        persistence_store: EventPersistenceStore | None = None,
        default_alpha: float = 1.0,
        default_beta: float = 1.0,
    ) -> None:
        if default_alpha <= 0 or default_beta <= 0:
            raise ValueError("default_alpha/default_beta must be positive.")
        self._default_alpha = float(default_alpha)
        self._default_beta = float(default_beta)
        self._store = persistence_store
        self._states: dict[str, BayesianState] = {}

    @staticmethod
    def _probability(alpha: float, beta: float) -> float:
        denom = alpha + beta
        if denom <= 0:
            return 0.5
        return float(alpha / denom)

    def get_state(self, market_id: str) -> BayesianState:
        key = str(market_id).strip()
        if not key:
            raise ValueError("market_id is required.")
        state = self._states.get(key)
        if state is not None:
            return state
        probability = self._probability(self._default_alpha, self._default_beta)
        seeded = BayesianState(
            market_id=key,
            alpha=self._default_alpha,
            beta=self._default_beta,
            prior_probability=probability,
            posterior_probability=probability,
            updated_at=_utc_now_iso(),
        )
        self._states[key] = seeded
        return seeded

    def update(
        self,
        *,
        market_id: str,
        evidence_successes: float,
        evidence_failures: float,
        evidence_weight: float = 1.0,
        evidence_source: str = "unknown",
        evidence_metadata: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> BayesianUpdateRecord:
        if evidence_successes < 0 or evidence_failures < 0:
            raise ValueError("evidence_successes/evidence_failures must be >= 0.")
        if evidence_weight <= 0:
            raise ValueError("evidence_weight must be > 0.")

        prior = self.get_state(market_id)
        prior_alpha = prior.alpha
        prior_beta = prior.beta
        prior_probability = self._probability(prior_alpha, prior_beta)

        delta_alpha = float(evidence_successes) * float(evidence_weight)
        delta_beta = float(evidence_failures) * float(evidence_weight)
        posterior_alpha = prior_alpha + delta_alpha
        posterior_beta = prior_beta + delta_beta
        posterior_probability = self._probability(posterior_alpha, posterior_beta)

        updated_at = str(timestamp or _utc_now_iso())
        update_record = BayesianUpdateRecord(
            market_id=prior.market_id,
            prior_alpha=prior_alpha,
            prior_beta=prior_beta,
            posterior_alpha=posterior_alpha,
            posterior_beta=posterior_beta,
            prior_probability=prior_probability,
            posterior_probability=posterior_probability,
            evidence_successes=float(evidence_successes),
            evidence_failures=float(evidence_failures),
            evidence_weight=float(evidence_weight),
            evidence_source=str(evidence_source).strip() or "unknown",
            evidence_metadata=dict(evidence_metadata or {}),
            updated_at=updated_at,
        )

        self._states[prior.market_id] = BayesianState(
            market_id=prior.market_id,
            alpha=posterior_alpha,
            beta=posterior_beta,
            prior_probability=prior_probability,
            posterior_probability=posterior_probability,
            updated_at=updated_at,
        )

        if self._store is not None:
            self._store.append(
                category="bayesian_probability_updates",
                payload=update_record.to_dict(),
                timestamp=updated_at,
            )

        return update_record

    def replay_persisted_updates(self, *, market_id: str | None = None) -> list[BayesianUpdateRecord]:
        if self._store is None:
            return []
        records = self._store.read(category="bayesian_probability_updates", limit=100000)
        updates: list[BayesianUpdateRecord] = []
        for row in reversed(records):
            payload = dict(row.payload)
            if market_id is not None and str(payload.get("market_id")) != str(market_id):
                continue
            updates.append(BayesianUpdateRecord(**payload))
        return updates
