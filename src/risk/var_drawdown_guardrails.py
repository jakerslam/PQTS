"""Portfolio VaR + drawdown guardrails with automatic new-risk gating."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Sequence

import numpy as np

from core.persistence import EventPersistenceStore


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


@dataclass(frozen=True)
class VarDrawdownConfig:
    var95_limit_pct: float = 0.030
    var99_limit_pct: float = 0.050
    drawdown_soft_limit_pct: float = 0.080
    drawdown_hard_limit_pct: float = 0.120
    reduce_new_risk_multiplier: float = 0.40
    min_capital: float = 1.0


@dataclass(frozen=True)
class VarMetrics:
    var95_pct: float
    var99_pct: float
    sample_size: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NewRiskGateDecision:
    action: str
    allowed_new_risk: bool
    max_new_risk_delta_usd: float
    reason: str
    metrics: dict[str, float]
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VarDrawdownGuardrail:
    """Evaluate VaR/drawdown stress and gate additional risk deterministically."""

    def __init__(
        self,
        *,
        config: VarDrawdownConfig | None = None,
        persistence_store: EventPersistenceStore | None = None,
    ) -> None:
        self.config = config or VarDrawdownConfig()
        self._store = persistence_store

    def compute_var_metrics(self, *, pnl_changes: Sequence[float], capital: float) -> VarMetrics:
        cap = max(_as_float(capital), self.config.min_capital)
        rows = np.asarray(list(pnl_changes), dtype=float)
        if rows.size == 0:
            return VarMetrics(var95_pct=0.0, var99_pct=0.0, sample_size=0)
        var95 = abs(float(np.percentile(rows, 5))) / cap
        var99 = abs(float(np.percentile(rows, 1))) / cap
        return VarMetrics(var95_pct=var95, var99_pct=var99, sample_size=int(rows.size))

    def evaluate(
        self,
        *,
        capital: float,
        current_drawdown_pct: float,
        pnl_changes: Sequence[float],
        proposed_new_risk_delta_usd: float,
        risk_budget_usd: float,
        timestamp: str | None = None,
    ) -> NewRiskGateDecision:
        cap = max(_as_float(capital), self.config.min_capital)
        drawdown = max(_as_float(current_drawdown_pct), 0.0)
        proposed_delta = _as_float(proposed_new_risk_delta_usd)
        budget = max(_as_float(risk_budget_usd), 0.0)
        var_metrics = self.compute_var_metrics(pnl_changes=pnl_changes, capital=cap)

        hard_breach = (
            drawdown >= self.config.drawdown_hard_limit_pct
            or var_metrics.var99_pct >= self.config.var99_limit_pct
        )
        soft_breach = (
            drawdown >= self.config.drawdown_soft_limit_pct
            or var_metrics.var95_pct >= self.config.var95_limit_pct
        )

        allow_risk_reduction_only = hard_breach
        if hard_breach:
            action = "block_new_risk"
            if proposed_delta <= 0.0:
                allowed = True
                max_delta = 0.0
                reason = (
                    "Hard VaR/drawdown breach; new risk blocked but de-risking trades remain allowed."
                )
            else:
                allowed = False
                max_delta = 0.0
                reason = "Hard VaR/drawdown breach; block new risk immediately."
        elif soft_breach:
            action = "reduce_new_risk"
            max_delta = budget * float(self.config.reduce_new_risk_multiplier)
            if proposed_delta <= 0.0:
                allowed = True
            else:
                allowed = proposed_delta <= max_delta
            reason = (
                "Soft VaR/drawdown breach; cap incremental risk until metrics recover."
            )
        else:
            action = "allow_new_risk"
            max_delta = budget
            allowed = proposed_delta <= max_delta
            reason = "VaR/drawdown within policy."

        ts = str(timestamp or _utc_now_iso())
        decision = NewRiskGateDecision(
            action=action,
            allowed_new_risk=bool(allowed),
            max_new_risk_delta_usd=float(max_delta),
            reason=reason,
            metrics={
                "drawdown_pct": float(drawdown),
                "var95_pct": float(var_metrics.var95_pct),
                "var99_pct": float(var_metrics.var99_pct),
                "proposed_new_risk_delta_usd": float(proposed_delta),
                "risk_budget_usd": float(budget),
                "allow_risk_reduction_only": 1.0 if allow_risk_reduction_only else 0.0,
            },
            timestamp=ts,
        )

        if self._store is not None:
            self._store.append(
                category="var_drawdown_guardrail_decisions",
                payload={
                    "decision": decision.to_dict(),
                    "var_metrics": var_metrics.to_dict(),
                },
                timestamp=ts,
            )
        return decision

    def replay_decisions(self) -> list[NewRiskGateDecision]:
        if self._store is None:
            return []
        rows = self._store.read(category="var_drawdown_guardrail_decisions", limit=100000)
        out: list[NewRiskGateDecision] = []
        for row in reversed(rows):
            payload = dict(row.payload).get("decision", {})
            if isinstance(payload, dict):
                out.append(NewRiskGateDecision(**payload))
        return out
