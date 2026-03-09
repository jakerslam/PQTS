"""Uncertainty-adjusted fractional Kelly sizing with edge/cap guardrails."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class UncertaintyKellyConfig:
    base_fraction: float = 0.5
    max_fraction: float = 0.25
    min_edge: float = 0.02
    uncertainty_penalty: float = 1.5


@dataclass(frozen=True)
class KellySizingDecision:
    market_id: str
    posterior_probability: float
    implied_probability: float
    edge: float
    full_kelly_fraction: float
    adjusted_fraction: float
    final_fraction: float
    blocked: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clip(value: float, low: float, high: float) -> float:
    return min(max(float(value), low), high)


def implied_probability_from_payout(payout_multiple: float) -> float:
    """Convert payout multiple `b` (net odds) to implied probability 1/(1+b)."""
    b = float(payout_multiple)
    if b <= 0:
        raise ValueError("payout_multiple must be > 0.")
    return 1.0 / (1.0 + b)


def full_kelly_fraction(*, posterior_probability: float, payout_multiple: float) -> float:
    p = _clip(float(posterior_probability), 0.0, 1.0)
    q = 1.0 - p
    b = float(payout_multiple)
    if b <= 0:
        raise ValueError("payout_multiple must be > 0.")
    return (p * b - q) / b


def uncertainty_adjusted_kelly(
    *,
    market_id: str,
    posterior_probability: float,
    payout_multiple: float,
    uncertainty: float,
    config: UncertaintyKellyConfig | None = None,
) -> KellySizingDecision:
    cfg = config or UncertaintyKellyConfig()
    posterior = _clip(float(posterior_probability), 0.0, 1.0)
    implied = implied_probability_from_payout(payout_multiple)
    edge = posterior - implied
    if edge < float(cfg.min_edge):
        return KellySizingDecision(
            market_id=str(market_id),
            posterior_probability=posterior,
            implied_probability=implied,
            edge=edge,
            full_kelly_fraction=0.0,
            adjusted_fraction=0.0,
            final_fraction=0.0,
            blocked=True,
            reason="edge_below_minimum",
        )

    full_kelly = full_kelly_fraction(
        posterior_probability=posterior,
        payout_multiple=payout_multiple,
    )
    full_kelly = max(full_kelly, 0.0)
    penalty_scalar = max(0.0, 1.0 - (float(cfg.uncertainty_penalty) * max(float(uncertainty), 0.0)))
    adjusted = full_kelly * float(cfg.base_fraction) * penalty_scalar
    final = _clip(adjusted, 0.0, float(cfg.max_fraction))
    return KellySizingDecision(
        market_id=str(market_id),
        posterior_probability=posterior,
        implied_probability=implied,
        edge=edge,
        full_kelly_fraction=full_kelly,
        adjusted_fraction=adjusted,
        final_fraction=final,
        blocked=final <= 0.0,
        reason="ok" if final > 0.0 else "fully_penalized",
    )


def batch_uncertainty_kelly(
    *,
    opportunities: list[dict[str, Any]],
    config: UncertaintyKellyConfig | None = None,
) -> list[KellySizingDecision]:
    cfg = config or UncertaintyKellyConfig()
    results: list[KellySizingDecision] = []
    for row in opportunities:
        results.append(
            uncertainty_adjusted_kelly(
                market_id=str(row.get("market_id", "unknown")),
                posterior_probability=float(row.get("posterior_probability", 0.0)),
                payout_multiple=float(row.get("payout_multiple", 1.0)),
                uncertainty=float(row.get("uncertainty", 0.0)),
                config=cfg,
            )
        )
    return results
