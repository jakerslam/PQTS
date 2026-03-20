"""Order-book quant stack controls for Avellaneda-Stoikov/Hawkes/VPIN (ZSTF)."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import List, Tuple


@dataclass(frozen=True)
class AvellanedaStoikovQuote:
    reservation_price: float
    spread: float
    bid: float
    ask: float
    inventory_skew: float


@dataclass(frozen=True)
class HawkesIntensityDecision:
    stable: bool
    baseline_intensity: float
    excitation: float
    decay: float
    estimated_intensity: float
    action: str
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class VpinCircuitDecision:
    action: str
    aggressiveness_multiplier: float
    cooldown_required: bool
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class MicrostructureSimulationDecision:
    promotion_allowed: bool
    reason_codes: Tuple[str, ...]
    spread_capture_mean: float
    drawdown_tail_p95: float
    toxicity_trigger_rate: float


@dataclass(frozen=True)
class SourceClaimDecision:
    verification_status: str
    allow_public_claim: bool
    reason_codes: Tuple[str, ...]


def compute_avellaneda_stoikov_quote(
    *,
    mid_price: float,
    inventory: float,
    risk_aversion: float,
    inventory_penalty: float,
    horizon_seconds: int,
    base_spread_bps: float,
    max_inventory_abs: float,
) -> AvellanedaStoikovQuote:
    inv = max(min(float(inventory), float(max_inventory_abs)), -float(max_inventory_abs))
    skew = float(risk_aversion) * float(inventory_penalty) * inv
    reservation = float(mid_price) - skew
    spread = max(float(base_spread_bps) / 10000.0 * float(mid_price), 0.0)
    if int(horizon_seconds) <= 0:
        spread *= 1.5
    bid = max(reservation - (spread / 2.0), 0.0)
    ask = max(reservation + (spread / 2.0), bid)
    return AvellanedaStoikovQuote(
        reservation_price=float(reservation),
        spread=float(spread),
        bid=float(bid),
        ask=float(ask),
        inventory_skew=float(skew),
    )


def evaluate_hawkes_intensity(
    *,
    baseline_intensity: float,
    excitation: float,
    decay: float,
    recent_event_count: int,
    max_intensity: float,
) -> HawkesIntensityDecision:
    reasons: List[str] = []
    stable = True

    if float(decay) <= 0.0:
        reasons.append("invalid_decay")
        stable = False
    if float(excitation) < 0.0:
        reasons.append("invalid_excitation")
        stable = False

    estimated = float(baseline_intensity) + float(excitation) * float(recent_event_count)
    if estimated < 0.0:
        estimated = 0.0
    if estimated > float(max_intensity):
        reasons.append("intensity_saturation")
        stable = False

    action = "allow" if stable else "fallback_conservative"
    return HawkesIntensityDecision(
        stable=stable,
        baseline_intensity=float(baseline_intensity),
        excitation=float(excitation),
        decay=float(decay),
        estimated_intensity=float(estimated),
        action=action,
        reason_codes=tuple(sorted(set(reasons))),
    )


def evaluate_vpin_circuit(
    *,
    vpin: float,
    high_threshold: float,
    medium_threshold: float,
    cooldown_elapsed_seconds: int,
    min_cooldown_seconds: int,
    health_revalidated: bool,
) -> VpinCircuitDecision:
    reasons: List[str] = []
    action = "normal"
    multiplier = 1.0
    cooldown_required = False

    if float(vpin) >= float(high_threshold):
        action = "pause"
        multiplier = 0.0
        cooldown_required = True
        reasons.append("vpin_high_toxicity")
    elif float(vpin) >= float(medium_threshold):
        action = "throttle"
        multiplier = 0.4
        reasons.append("vpin_medium_toxicity")

    if action in {"pause", "throttle"}:
        if int(cooldown_elapsed_seconds) < int(min_cooldown_seconds):
            reasons.append("cooldown_not_elapsed")
        if not health_revalidated:
            reasons.append("health_not_revalidated")

    if action == "pause" and int(cooldown_elapsed_seconds) >= int(min_cooldown_seconds) and health_revalidated:
        action = "resume"
        multiplier = 0.6
        cooldown_required = False

    return VpinCircuitDecision(
        action=action,
        aggressiveness_multiplier=float(multiplier),
        cooldown_required=bool(cooldown_required),
        reason_codes=tuple(sorted(set(reasons))),
    )


def evaluate_microstructure_simulation(
    *,
    spread_capture_series: List[float],
    drawdown_tail_p95: float,
    toxicity_trigger_rate: float,
    min_spread_capture_mean: float,
    max_drawdown_tail_p95: float,
    max_toxicity_trigger_rate: float,
) -> MicrostructureSimulationDecision:
    reasons: List[str] = []
    spread_mean = float(mean(spread_capture_series)) if spread_capture_series else 0.0
    if spread_mean < float(min_spread_capture_mean):
        reasons.append("spread_capture_below_threshold")
    if float(drawdown_tail_p95) > float(max_drawdown_tail_p95):
        reasons.append("drawdown_tail_exceeded")
    if float(toxicity_trigger_rate) > float(max_toxicity_trigger_rate):
        reasons.append("toxicity_trigger_rate_exceeded")

    return MicrostructureSimulationDecision(
        promotion_allowed=not bool(reasons),
        reason_codes=tuple(sorted(set(reasons))),
        spread_capture_mean=spread_mean,
        drawdown_tail_p95=float(drawdown_tail_p95),
        toxicity_trigger_rate=float(toxicity_trigger_rate),
    )


def evaluate_source_claim(
    *,
    has_trade_level_replay: bool,
    has_controlled_rerun: bool,
) -> SourceClaimDecision:
    reasons: List[str] = []
    if not has_trade_level_replay:
        reasons.append("missing_trade_level_replay")
    if not has_controlled_rerun:
        reasons.append("missing_controlled_rerun")

    verified = not bool(reasons)
    return SourceClaimDecision(
        verification_status="verified" if verified else "unverified",
        allow_public_claim=verified,
        reason_codes=tuple(sorted(set(reasons))),
    )
