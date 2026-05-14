"""Tests for observable Markov-regime research helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from research.markov_regime import (  # noqa: E402
    BULL_STATE,
    MarkovRegimeConfig,
    build_walkforward_markov_signal,
    define_observable_market_states,
    estimate_transition_matrix,
    forecast_state_probabilities,
    stationary_distribution,
)


def test_observable_state_labels_keep_warmup_unknown():
    returns = pd.Series([0.01, 0.01, 0.01, -0.02, 0.0])

    states = define_observable_market_states(
        returns,
        bull_threshold=0.02,
        bear_threshold=-0.02,
        window=3,
    )

    assert states.iloc[:2].isna().all()
    assert int(states.iloc[2]) == BULL_STATE


def test_transition_matrix_uses_observed_counts_and_stays_row_stochastic():
    states = pd.Series([0, 0, 1, 1, 2, 0], dtype=float)

    estimate = estimate_transition_matrix(states, smoothing=0.0)

    assert np.allclose(estimate.matrix.sum(axis=1), 1.0)
    assert np.allclose(estimate.counts[0], [1.0, 1.0, 0.0])
    assert np.allclose(estimate.matrix[0], [0.5, 0.5, 0.0])


def test_transition_matrix_does_not_bridge_missing_state_gaps():
    states = pd.Series([0, np.nan, 1, 1], dtype=float)

    estimate = estimate_transition_matrix(states, smoothing=0.0)

    assert estimate.counts[0].sum() == 0.0
    assert estimate.counts[1, 1] == 1.0


def test_forecast_and_stationary_distribution_are_probabilities():
    states = pd.Series([0, 0, 1, 1, 2, 0, 0, 2, 2, 0], dtype=float)
    estimate = estimate_transition_matrix(states, smoothing=1.0)

    forecast = forecast_state_probabilities(
        estimate.matrix,
        current_state=BULL_STATE,
        n_steps=3,
    )
    stationary = stationary_distribution(estimate.matrix)

    assert np.isclose(forecast.sum(), 1.0)
    assert np.isclose(stationary.sum(), 1.0)
    assert (forecast >= 0.0).all()
    assert (stationary >= 0.0).all()


def test_walkforward_signal_uses_past_transition_counts():
    index = pd.date_range("2025-01-01", periods=80, freq="h")
    returns = pd.Series(0.004, index=index)
    returns.iloc[40:48] = -0.004
    config = MarkovRegimeConfig(
        regime_window=3,
        transition_lookback=12,
        bull_threshold=0.006,
        bear_threshold=-0.006,
        signal_threshold=0.01,
        smoothing=0.1,
        min_row_transitions=1,
        forecast_steps=1,
    )

    signal = build_walkforward_markov_signal(returns, config)

    assert signal.iloc[:12].eq(0.0).all()
    assert signal.iloc[-1] > 0.0
    assert signal.min() >= -1.0
    assert signal.max() <= 1.0
