"""Cost/capacity-aware strategy capital allocator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import numpy as np


@dataclass(frozen=True)
class StrategyBudgetInput:
    strategy_id: str
    expected_return: float
    annual_vol: float
    annual_turnover: float
    cost_per_turnover: float
    capacity_ratio: float


@dataclass(frozen=True)
class StrategyUtilityConfig:
    """Risk-utility parameters for capital allocation."""

    risk_aversion: float = 4.0
    turnover_penalty: float = 1.0
    capacity_penalty: float = 1.0


class StrategyCapitalAllocator:
    """Allocate capital weights across strategies using utility-aware controls."""

    def __init__(
        self,
        max_weight: float = 0.35,
        min_weight: float = 0.0,
        capacity_haircut: float = 0.05,
        utility_config: Optional[StrategyUtilityConfig] = None,
    ):
        self.max_weight = float(max_weight)
        self.min_weight = float(min_weight)
        self.capacity_haircut = float(capacity_haircut)
        self.utility_config = utility_config or StrategyUtilityConfig()

    def net_edge(self, item: StrategyBudgetInput) -> float:
        cost_drag = float(item.annual_turnover) * float(item.cost_per_turnover)
        capacity_drag = max(float(item.capacity_ratio) - 1.0, 0.0) * self.capacity_haircut
        return float(item.expected_return) - cost_drag - capacity_drag

    def utility_score(
        self,
        item: StrategyBudgetInput,
        *,
        utility: Optional[StrategyUtilityConfig] = None,
    ) -> float:
        """
        Compute strategy utility as net edge minus risk/cost penalties.

        U = net_edge - lambda*vol^2 - turnover_penalty*cost_drag - capacity_penalty*over_capacity
        """
        cfg = utility or self.utility_config
        net_edge = self.net_edge(item)
        variance_penalty = float(cfg.risk_aversion) * float(item.annual_vol) ** 2
        turnover_penalty = float(cfg.turnover_penalty) * (
            float(item.annual_turnover) * float(item.cost_per_turnover)
        )
        over_capacity = max(float(item.capacity_ratio) - 1.0, 0.0)
        capacity_penalty = float(cfg.capacity_penalty) * over_capacity
        return net_edge - variance_penalty - turnover_penalty - capacity_penalty

    @staticmethod
    def _normalize(weights: np.ndarray) -> np.ndarray:
        positive = np.maximum(weights, 0.0)
        total = float(positive.sum())
        if total <= 1e-12:
            return np.full(len(weights), 1.0 / max(len(weights), 1), dtype=float)
        return positive / total

    def _clip(self, weights: np.ndarray) -> np.ndarray:
        clipped = np.clip(weights, self.min_weight, self.max_weight)
        total = float(clipped.sum())
        if total <= 1e-12:
            return np.full(len(weights), 1.0 / max(len(weights), 1), dtype=float)
        return clipped / total

    def allocate_utility(
        self,
        inputs: Iterable[StrategyBudgetInput],
        *,
        utility: Optional[StrategyUtilityConfig] = None,
    ) -> Dict[str, float]:
        """
        Utility-based allocation maximizing risk-adjusted expected net alpha.

        Base score = utility / vol; then normalized + box-constrained.
        """
        rows: List[StrategyBudgetInput] = list(inputs)
        if not rows:
            return {}

        cfg = utility or self.utility_config
        utilities = np.array(
            [self.utility_score(row, utility=cfg) for row in rows],
            dtype=float,
        )
        vols = np.array([max(float(row.annual_vol), 1e-6) for row in rows], dtype=float)
        utility_per_risk = utilities / vols
        shifted = utility_per_risk - float(np.min(utility_per_risk))
        if float(np.sum(shifted)) <= 1e-12:
            shifted = np.ones_like(utility_per_risk)
        base = self._normalize(shifted)
        clipped = self._clip(base)
        return {row.strategy_id: float(weight) for row, weight in zip(rows, clipped)}

    def allocate(self, inputs: Iterable[StrategyBudgetInput]) -> Dict[str, float]:
        """Backward-compatible alias: now delegates to utility-based allocation."""
        return self.allocate_utility(inputs, utility=self.utility_config)
