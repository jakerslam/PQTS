"""Underdog-value signal and sizing primitives."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import exp
from typing import Mapping


@dataclass(frozen=True)
class QuoteSnapshot:
    market_id: str
    outcome_id: str
    yes_price: float
    no_price: float
    timestamp_ms: int
    venue: str
    depth: float = 0.0


@dataclass(frozen=True)
class CalibrationMetrics:
    brier_score: float
    calibration_error: float
    sample_size: int


@dataclass(frozen=True)
class UnderdogValueConfig:
    underdog_max_prob: float = 0.50
    min_edge: float = 0.03
    min_net_ev: float = 0.0
    min_depth: float = 100.0
    fee_bps: float = 10.0
    slippage_bps: float = 5.0
    kelly_fraction: float = 0.50
    max_position_fraction: float = 0.02
    max_event_exposure: float = 0.05
    max_strategy_exposure: float = 0.20
    disable_rolling_edge_floor: float = -0.01
    convergence_threshold: float = 0.01


@dataclass(frozen=True)
class SignalDecision:
    allowed: bool
    reason: str
    p_market: float
    p_model: float
    edge: float
    net_ev: float


@dataclass(frozen=True)
class PositionSizingDecision:
    requested_fraction: float
    approved_fraction: float
    blocked: bool
    reason: str


class UnderdogValueStrategy:
    """Core underdog-value logic used by backtest and paper/live control paths."""

    def __init__(self, config: UnderdogValueConfig | None = None) -> None:
        self.config = config or UnderdogValueConfig()

    @staticmethod
    def normalize_market_probability(snapshot: QuoteSnapshot) -> float:
        total = float(snapshot.yes_price) + float(snapshot.no_price)
        if total <= 0.0:
            raise ValueError("yes_price + no_price must be positive")
        return float(snapshot.yes_price) / total

    @staticmethod
    def classify_calibration(
        metrics: CalibrationMetrics,
        *,
        max_brier: float = 0.25,
        max_calibration_error: float = 0.08,
        min_samples: int = 200,
    ) -> bool:
        return (
            metrics.brier_score <= max_brier
            and metrics.calibration_error <= max_calibration_error
            and metrics.sample_size >= min_samples
        )

    @staticmethod
    def estimate_fair_probability(
        features: Mapping[str, float],
        *,
        weights: Mapping[str, float] | None = None,
        bias: float = 0.0,
    ) -> float:
        # Sorted iteration keeps runs deterministic for the same input map.
        linear = float(bias)
        for name in sorted(features):
            weight = 1.0 if weights is None else float(weights.get(name, 1.0))
            linear += float(features[name]) * weight
        return 1.0 / (1.0 + exp(-linear))

    def evaluate_signal(
        self,
        snapshot: QuoteSnapshot,
        *,
        p_model: float,
        liquidity_ok: bool = True,
        capacity_ok: bool = True,
    ) -> SignalDecision:
        p_market = self.normalize_market_probability(snapshot)
        p_model = float(max(0.0, min(1.0, p_model)))
        edge = p_model - p_market
        estimated_cost = (self.config.fee_bps + self.config.slippage_bps) / 10_000.0
        net_ev = edge - estimated_cost

        if p_market >= self.config.underdog_max_prob:
            return SignalDecision(False, "not_underdog", p_market, p_model, edge, net_ev)
        if snapshot.depth < self.config.min_depth:
            return SignalDecision(False, "insufficient_depth", p_market, p_model, edge, net_ev)
        if not liquidity_ok:
            return SignalDecision(False, "liquidity_gate", p_market, p_model, edge, net_ev)
        if not capacity_ok:
            return SignalDecision(False, "capacity_gate", p_market, p_model, edge, net_ev)
        if edge < self.config.min_edge:
            return SignalDecision(False, "edge_below_threshold", p_market, p_model, edge, net_ev)
        if net_ev <= self.config.min_net_ev:
            return SignalDecision(False, "net_ev_non_positive", p_market, p_model, edge, net_ev)
        return SignalDecision(True, "accepted", p_market, p_model, edge, net_ev)

    def size_position(
        self,
        *,
        decision: SignalDecision,
        payout_multiple: float,
        event_exposure: float,
        strategy_exposure: float,
        rolling_realized_edge: float,
    ) -> PositionSizingDecision:
        if not decision.allowed:
            return PositionSizingDecision(0.0, 0.0, True, f"blocked:{decision.reason}")
        if rolling_realized_edge < self.config.disable_rolling_edge_floor:
            return PositionSizingDecision(0.0, 0.0, True, "rolling_edge_disable")

        b = max(float(payout_multiple), 0.0001)
        p = decision.p_model
        q = 1.0 - p
        full_kelly = max(((b * p) - q) / b, 0.0)
        requested = full_kelly * self.config.kelly_fraction

        risk_cap = min(
            self.config.max_position_fraction,
            max(self.config.max_event_exposure - event_exposure, 0.0),
            max(self.config.max_strategy_exposure - strategy_exposure, 0.0),
        )
        approved = max(min(requested, risk_cap), 0.0)
        blocked = approved <= 0.0
        reason = "approved" if not blocked else "exposure_cap"
        return PositionSizingDecision(requested, approved, blocked, reason)

    def choose_exit_mode(
        self,
        *,
        mark_probability: float,
        fair_probability: float,
        stop_loss_hit: bool = False,
        time_stop_hit: bool = False,
        event_resolved: bool = False,
        risk_forced_unwind: bool = False,
    ) -> str:
        if risk_forced_unwind:
            return "risk_forced_exit"
        if event_resolved:
            return "held_to_resolution"
        if stop_loss_hit or time_stop_hit:
            return "early_exit_policy"
        if abs(float(mark_probability) - float(fair_probability)) <= (self.config.convergence_threshold + 1e-12):
            return "fair_value_convergence"
        return "hold"

    @staticmethod
    def signal_telemetry(
        snapshot: QuoteSnapshot,
        *,
        decision: SignalDecision,
        expected_ev: float,
    ) -> dict[str, float | str | bool]:
        return {
            "market_id": snapshot.market_id,
            "outcome_id": snapshot.outcome_id,
            "venue": snapshot.venue,
            "quote_ts_ms": snapshot.timestamp_ms,
            "p_market": decision.p_market,
            "p_model": decision.p_model,
            "edge": decision.edge,
            "expected_ev": float(expected_ev),
            "estimated_fee_slippage_bps": float(
                (UnderdogValueConfig().fee_bps + UnderdogValueConfig().slippage_bps)
            ),
            "decision_allowed": decision.allowed,
            "decision_reason": decision.reason,
        }

    @staticmethod
    def realized_vs_expected_diagnostics(*, realized_ev: float, expected_ev: float) -> dict[str, float]:
        delta = float(realized_ev) - float(expected_ev)
        return {
            "expected_ev": float(expected_ev),
            "realized_ev": float(realized_ev),
            "delta_ev": delta,
            "delta_bps": delta * 10_000.0,
        }

    @staticmethod
    def to_dict(value: SignalDecision | PositionSizingDecision | CalibrationMetrics) -> dict[str, object]:
        return asdict(value)
