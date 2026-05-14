"""Observable Markov-chain regime helpers for research-only strategy validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd


BULL_STATE = 0
BEAR_STATE = 1
SIDEWAYS_STATE = 2
DEFAULT_STATE_NAMES: Tuple[str, str, str] = ("Bull", "Bear", "Sideways")


@dataclass(frozen=True)
class MarkovRegimeConfig:
    """Configuration for a walk-forward observable Markov regime model."""

    regime_window: int = 20
    transition_lookback: int = 252
    bull_threshold: float = 0.02
    bear_threshold: float = -0.02
    signal_threshold: float = 0.10
    smoothing: float = 1.0
    min_row_transitions: int = 5
    forecast_steps: int = 1


@dataclass(frozen=True)
class TransitionMatrixEstimate:
    """Transition estimate plus the counts needed for reliability gates."""

    matrix: np.ndarray
    counts: np.ndarray
    row_transition_counts: np.ndarray

    def row_is_sufficient(self, state: int, min_transitions: int) -> bool:
        if state < 0 or state >= len(self.row_transition_counts):
            return False
        return bool(self.row_transition_counts[state] >= max(int(min_transitions), 0))


def define_observable_market_states(
    returns: pd.Series,
    *,
    bull_threshold: float = 0.02,
    bear_threshold: float = -0.02,
    window: int = 20,
) -> pd.Series:
    """
    Label returns as bull, bear, or sideways regimes using only trailing data.

    Early rows with insufficient trailing history remain NaN instead of being
    silently treated as sideways.
    """

    if bull_threshold <= bear_threshold:
        raise ValueError("bull_threshold must be greater than bear_threshold")
    lookback = max(int(window), 1)
    clean_returns = pd.to_numeric(returns, errors="coerce").replace([np.inf, -np.inf], np.nan)
    rolling_return = clean_returns.rolling(lookback, min_periods=lookback).sum()

    states = pd.Series(np.nan, index=returns.index, dtype=float)
    known = rolling_return.notna()
    states.loc[known & (rolling_return > float(bull_threshold))] = float(BULL_STATE)
    states.loc[known & (rolling_return < float(bear_threshold))] = float(BEAR_STATE)
    states.loc[
        known
        & (rolling_return <= float(bull_threshold))
        & (rolling_return >= float(bear_threshold))
    ] = float(SIDEWAYS_STATE)
    return states


def estimate_transition_matrix(
    states: pd.Series,
    *,
    n_states: int = 3,
    smoothing: float = 1.0,
) -> TransitionMatrixEstimate:
    """Estimate a row-stochastic transition matrix from observed state labels."""

    state_count = max(int(n_states), 1)
    prior = max(float(smoothing), 0.0)
    counts = np.zeros((state_count, state_count), dtype=float)
    values = pd.to_numeric(states, errors="coerce").to_numpy(dtype=float)

    for current_state, next_state in zip(values[:-1], values[1:]):
        if np.isnan(current_state) or np.isnan(next_state):
            continue
        current = int(current_state)
        next_ = int(next_state)
        if 0 <= current < state_count and 0 <= next_ < state_count:
            counts[current, next_] += 1.0

    matrix = counts + prior
    row_sums = matrix.sum(axis=1, keepdims=True)
    zero_rows = row_sums[:, 0] <= 0.0
    row_sums[zero_rows, 0] = 1.0
    matrix = matrix / row_sums
    if np.any(zero_rows):
        matrix[zero_rows, :] = 1.0 / float(state_count)

    return TransitionMatrixEstimate(
        matrix=matrix,
        counts=counts,
        row_transition_counts=counts.sum(axis=1),
    )


def multi_step_transition(matrix: np.ndarray, n_steps: int) -> np.ndarray:
    """Return the n-step transition matrix."""

    steps = max(int(n_steps), 1)
    return np.linalg.matrix_power(np.asarray(matrix, dtype=float), steps)


def forecast_state_probabilities(
    matrix: np.ndarray,
    *,
    current_state: int,
    n_steps: int = 1,
) -> np.ndarray:
    """Forecast future state probabilities from a current state."""

    state = int(current_state)
    transition = multi_step_transition(matrix, n_steps)
    if state < 0 or state >= transition.shape[0]:
        return np.ones(transition.shape[1], dtype=float) / float(transition.shape[1])
    return transition[state]


def stationary_distribution(matrix: np.ndarray) -> np.ndarray:
    """Solve the long-run state distribution for a transition matrix."""

    transition = np.asarray(matrix, dtype=float)
    n_states = transition.shape[0]
    if transition.ndim != 2 or transition.shape[0] != transition.shape[1] or n_states == 0:
        raise ValueError("matrix must be a non-empty square array")

    a = transition.T - np.eye(n_states)
    a[-1] = 1.0
    b = np.zeros(n_states)
    b[-1] = 1.0
    try:
        result = np.linalg.solve(a, b)
    except np.linalg.LinAlgError:
        result = np.ones(n_states, dtype=float) / float(n_states)

    result = np.clip(result, 0.0, 1.0)
    total = float(result.sum())
    if total <= 1e-12:
        return np.ones(n_states, dtype=float) / float(n_states)
    return result / total


def build_walkforward_markov_signal(
    returns: pd.Series,
    config: MarkovRegimeConfig,
) -> pd.Series:
    """
    Build a walk-forward signal from rolling transition estimates.

    Each timestamp's transition matrix is estimated from state labels strictly
    before that timestamp. The current timestamp may use its already-observed
    trailing-return state, and downstream backtests still shift positions by one
    period before applying returns.
    """

    clean_returns = pd.to_numeric(returns, errors="coerce").replace([np.inf, -np.inf], np.nan)
    states = define_observable_market_states(
        clean_returns,
        bull_threshold=float(config.bull_threshold),
        bear_threshold=float(config.bear_threshold),
        window=int(config.regime_window),
    )
    signal = pd.Series(0.0, index=returns.index, dtype=float)
    lookback = max(int(config.transition_lookback), 2)
    threshold = max(float(config.signal_threshold), 0.0)

    for idx in range(lookback, len(states)):
        current_state_value = states.iloc[idx]
        if pd.isna(current_state_value):
            continue
        current_state = int(current_state_value)
        historical_states = states.iloc[idx - lookback : idx]
        estimate = estimate_transition_matrix(
            historical_states,
            n_states=3,
            smoothing=float(config.smoothing),
        )
        if not estimate.row_is_sufficient(current_state, int(config.min_row_transitions)):
            continue
        probabilities = forecast_state_probabilities(
            estimate.matrix,
            current_state=current_state,
            n_steps=int(config.forecast_steps),
        )
        raw_signal = float(probabilities[BULL_STATE] - probabilities[BEAR_STATE])
        if abs(raw_signal) < threshold:
            raw_signal = 0.0
        signal.iloc[idx] = float(np.clip(raw_signal, -1.0, 1.0))

    return signal
