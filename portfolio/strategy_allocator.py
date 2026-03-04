"""Cost/capacity-aware strategy capital allocator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List
import numpy as np


@dataclass(frozen=True)
class StrategyBudgetInput:
    strategy_id: str
    expected_return: float
    annual_vol: float
    annual_turnover: float
    cost_per_turnover: float
    capacity_ratio: float


class StrategyCapitalAllocator:
    """Allocate capital weights across strategies using net-edge and risk controls."""

    def __init__(
        self,
        max_weight: float = 0.35,
        min_weight: float = 0.0,
        capacity_haircut: float = 0.05,
    ):
        self.max_weight = float(max_weight)
        self.min_weight = float(min_weight)
        self.capacity_haircut = float(capacity_haircut)

    def net_edge(self, item: StrategyBudgetInput) -> float:
        cost_drag = float(item.annual_turnover) * float(item.cost_per_turnover)
        capacity_drag = max(float(item.capacity_ratio) - 1.0, 0.0) * self.capacity_haircut
        return float(item.expected_return) - cost_drag - capacity_drag

    def allocate(self, inputs: Iterable[StrategyBudgetInput]) -> Dict[str, float]:
        rows: List[StrategyBudgetInput] = list(inputs)
        if not rows:
            return {}

        scores = []
        for row in rows:
            edge = self.net_edge(row)
            risk = max(float(row.annual_vol), 1e-6)
            scores.append(edge / risk)
        scores_arr = np.array(scores, dtype=float)
        positive = np.maximum(scores_arr, 0.0)

        if float(positive.sum()) <= 1e-12:
            base = np.full(len(rows), 1.0 / len(rows), dtype=float)
        else:
            base = positive / positive.sum()

        clipped = np.clip(base, self.min_weight, self.max_weight)
        total = float(clipped.sum())
        if total <= 1e-12:
            clipped = np.full(len(rows), 1.0 / len(rows), dtype=float)
        else:
            clipped = clipped / total

        return {row.strategy_id: float(weight) for row, weight in zip(rows, clipped)}
