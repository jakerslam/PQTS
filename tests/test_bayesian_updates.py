"""Tests for Bayesian probability update engine."""

from __future__ import annotations

from core.persistence import EventPersistenceStore
from execution.bayesian_updates import BayesianProbabilityEngine


def test_bayesian_engine_updates_posterior_probability() -> None:
    engine = BayesianProbabilityEngine(default_alpha=2.0, default_beta=2.0)
    update = engine.update(
        market_id="btc_breakout",
        evidence_successes=3.0,
        evidence_failures=1.0,
        evidence_weight=1.0,
        evidence_source="signal_ensemble",
        evidence_metadata={"window": "5m"},
    )
    assert update.prior_probability == 0.5
    assert update.posterior_alpha == 5.0
    assert update.posterior_beta == 3.0
    assert update.posterior_probability == 5.0 / 8.0


def test_bayesian_engine_persists_prior_evidence_posterior_metadata(tmp_path) -> None:
    store = EventPersistenceStore(dsn=f"sqlite:///{tmp_path / 'events.db'}")
    engine = BayesianProbabilityEngine(persistence_store=store)
    _ = engine.update(
        market_id="eth_reversal",
        evidence_successes=2.0,
        evidence_failures=0.5,
        evidence_weight=0.75,
        evidence_source="orderbook_model",
        evidence_metadata={"venue": "binance"},
        timestamp="2026-03-09T00:00:00+00:00",
    )

    persisted = engine.replay_persisted_updates(market_id="eth_reversal")
    assert len(persisted) == 1
    row = persisted[0]
    assert row.market_id == "eth_reversal"
    assert row.prior_alpha == 1.0
    assert row.prior_beta == 1.0
    assert row.evidence_source == "orderbook_model"
    assert row.evidence_metadata["venue"] == "binance"
    assert row.updated_at == "2026-03-09T00:00:00+00:00"
