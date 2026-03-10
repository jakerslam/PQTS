"""Runtime bridge for optional native hot-path kernels with safe Python fallback."""

from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from typing import Any, Iterable


def _to_level_tuple(level: Any) -> tuple[float, float]:
    if not isinstance(level, (list, tuple)) or len(level) < 2:
        return 0.0, 0.0
    try:
        price = float(level[0])
        size = float(level[1])
    except (TypeError, ValueError):
        return 0.0, 0.0
    return max(price, 0.0), max(size, 0.0)


def _normalize_levels(levels: Iterable[Any], *, max_levels: int) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    max_rows = max(int(max_levels), 1)
    for level in levels:
        if len(out) >= max_rows:
            break
        out.append(_to_level_tuple(level))
    return out


@lru_cache(maxsize=1)
def _load_native_module() -> Any | None:
    env = os.getenv("PQTS_NATIVE_HOTPATH", "").strip().lower()
    if env in {"0", "false", "off", "no"}:
        return None
    try:
        import pqts_hotpath as module  # type: ignore
    except Exception:
        return None
    required_symbols = (
        "sum_notional",
        "fill_metrics",
        "sequence_transition",
        "uniform_from_seed",
        "event_id_hash",
        "paper_fill_metrics",
        "smart_router_score",
        "quote_state",
    )
    if any(not hasattr(module, symbol) for symbol in required_symbols):
        return None
    return module


def native_available() -> bool:
    return _load_native_module() is not None


def sum_notional(levels: Iterable[Any], *, max_levels: int = 5) -> float:
    normalized = _normalize_levels(levels, max_levels=max_levels)
    module = _load_native_module()
    if module is not None:
        try:
            return float(module.sum_notional(normalized, int(max(int(max_levels), 1))))
        except Exception:
            pass
    total = 0.0
    for price, size in normalized:
        total += price * size
    return float(total)


def fill_metrics(
    *,
    side: str,
    reference_price: float,
    executed_price: float,
    requested_qty: float,
    executed_qty: float,
) -> tuple[float, float]:
    side_token = str(side).lower()
    ref = float(reference_price)
    exe = float(executed_price)
    req = float(requested_qty)
    filled = float(executed_qty)
    module = _load_native_module()
    if module is not None and hasattr(module, "fill_metrics"):
        try:
            slippage_bps, fill_ratio = module.fill_metrics(side_token, ref, exe, req, filled)
            return float(slippage_bps), float(fill_ratio)
        except Exception:
            pass

    ref_denom = max(ref, 1e-12)
    if side_token == "buy":
        slip_pct = max((exe - ref) / ref_denom, 0.0)
    else:
        slip_pct = max((ref - exe) / ref_denom, 0.0)
    slippage_bps = float(slip_pct * 10000.0)
    fill_ratio = float(filled / max(req, 1e-12))
    return slippage_bps, fill_ratio


def sequence_transition(
    *,
    expected_sequence: int | None,
    received_sequence: int,
    allow_auto_recover: bool,
    snapshot_sequence: int | None,
) -> tuple[str, int, int, bool, int | None, int]:
    expected = int(expected_sequence) if expected_sequence is not None else None
    received = int(received_sequence)
    snapshot = int(snapshot_sequence) if snapshot_sequence is not None else None
    can_recover = bool(allow_auto_recover)

    module = _load_native_module()
    if module is not None and hasattr(module, "sequence_transition"):
        try:
            mode, event_expected, gap_size, recovered, applied_snapshot, next_expected = (
                module.sequence_transition(
                    received_sequence=received,
                    allow_auto_recover=can_recover,
                    expected_sequence=expected,
                    snapshot_sequence=snapshot,
                )
            )
            return (
                str(mode),
                int(event_expected),
                int(gap_size),
                bool(recovered),
                int(applied_snapshot) if applied_snapshot is not None else None,
                int(next_expected),
            )
        except Exception:
            pass

    if expected is None:
        next_expected = received + 1
        return "seed", next_expected, 0, False, None, next_expected
    if received < expected:
        return "stale_drop", expected, 0, False, None, expected
    if received == expected:
        return "in_order", expected, 0, False, None, received + 1
    gap_size = received - expected
    if can_recover and snapshot is not None:
        return "gap_recovered_snapshot", expected, gap_size, True, snapshot, snapshot + 1
    return "gap_detected", expected, gap_size, False, None, expected


def uniform_from_seed(seed: str) -> float:
    token = str(seed)
    module = _load_native_module()
    if module is not None and hasattr(module, "uniform_from_seed"):
        try:
            return float(module.uniform_from_seed(token))
        except Exception:
            pass
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / float(0xFFFFFFFF)


def event_id(prefix: str, parts: Iterable[Any], *, hex_len: int = 16) -> str:
    payload = "|".join(str(part) for part in parts)
    token_prefix = str(prefix).strip() or "evt"
    take = max(1, min(int(hex_len), 64))
    module = _load_native_module()
    if module is not None and hasattr(module, "event_id_hash"):
        try:
            return str(module.event_id_hash(token_prefix, payload, take))
        except Exception:
            pass
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:take]
    return f"{token_prefix}_{digest}"


def paper_fill_metrics(
    *,
    side: str,
    requested_qty: float,
    reference_price: float,
    queue_qty: float,
    partial_fill_notional_usd: float,
    min_partial_fill_ratio: float,
    queue_penalty_floor: float,
    adverse_selection_bps: float,
    min_slippage_bps: float,
    queue_slippage_bps_per_turnover: float,
    reality_stress_mode: bool,
    stress_fill_ratio_multiplier: float,
    stress_slippage_multiplier: float,
    fill_uniform: float,
    slippage_uniform: float,
) -> tuple[float, float, float, float, float]:
    req_qty = max(float(requested_qty), 0.0)
    ref_price = max(float(reference_price), 0.0)
    queue = max(float(queue_qty), 0.0)
    partial = max(float(partial_fill_notional_usd), 1e-9)
    min_fill = max(float(min_partial_fill_ratio), 0.0)
    min_fill = min(min_fill, 1.0)

    module = _load_native_module()
    if module is not None and hasattr(module, "paper_fill_metrics"):
        try:
            fill_ratio, slip_bps, executed_qty, executed_price, queue_turnover = module.paper_fill_metrics(
                str(side).lower(),
                req_qty,
                ref_price,
                queue,
                partial,
                min_fill,
                max(float(queue_penalty_floor), 0.0),
                max(float(adverse_selection_bps), 0.0),
                max(float(min_slippage_bps), 0.0),
                max(float(queue_slippage_bps_per_turnover), 0.0),
                bool(reality_stress_mode),
                max(float(stress_fill_ratio_multiplier), 0.0),
                max(float(stress_slippage_multiplier), 0.0),
                float(fill_uniform),
                float(slippage_uniform),
            )
            return (
                float(fill_ratio),
                float(slip_bps),
                float(executed_qty),
                float(executed_price),
                float(queue_turnover),
            )
        except Exception:
            pass

    notional = req_qty * ref_price
    if notional <= partial:
        base_fill_ratio = 1.0
    else:
        capacity_ratio = partial / max(notional, 1e-9)
        capacity_ratio = max(min(capacity_ratio, 1.0), min_fill)
        jitter = 0.9 + (0.2 * float(fill_uniform))
        base_fill_ratio = max(min(capacity_ratio * jitter, 1.0), min_fill)

    queue_notional = queue * ref_price
    order_notional = max(req_qty * ref_price, 1e-9)
    if queue_notional <= 0.0:
        queue_turnover = 0.0
    else:
        queue_turnover = order_notional / queue_notional

    queue_penalty = max(
        max(float(queue_penalty_floor), 0.0),
        1.0 / (1.0 + max(queue_turnover, 0.0)),
    )
    fill_ratio = base_fill_ratio * queue_penalty
    if bool(reality_stress_mode):
        fill_ratio *= max(float(stress_fill_ratio_multiplier), 0.0)
        fill_ratio = max(min(fill_ratio, 1.0), 0.0)

    impact_scale = max((notional / max(partial, 1e-9)) - 1.0, 0.0)
    stochastic_component = (float(slippage_uniform) - 0.5) * 0.6
    slip_bps = max(float(adverse_selection_bps), 0.0) * (0.5 + impact_scale) + stochastic_component
    slip_bps += max(float(queue_slippage_bps_per_turnover), 0.0) * max(queue_turnover, 0.0)
    slip_bps = max(float(slip_bps), max(float(min_slippage_bps), 0.0))
    if bool(reality_stress_mode):
        slip_bps *= max(float(stress_slippage_multiplier), 0.0)

    executed_qty = req_qty * fill_ratio
    if str(side).lower() == "buy":
        executed_price = ref_price * (1.0 + (slip_bps / 10000.0))
    else:
        executed_price = ref_price * (1.0 - (slip_bps / 10000.0))
    return (
        float(fill_ratio),
        float(slip_bps),
        float(executed_qty),
        float(executed_price),
        float(max(queue_turnover, 0.0)),
    )


def smart_router_score(
    *,
    spread: float,
    volume_24h: float,
    fee_bps: float,
    slippage_ratio: float,
    fill_ratio: float,
    latency_ms: float,
) -> float:
    spread_token = max(float(spread), 0.0)
    volume_token = max(float(volume_24h), 0.0)
    fee_token = float(fee_bps)
    slippage_token = max(float(slippage_ratio), 0.25)
    fill_token = max(min(float(fill_ratio), 1.0), 0.0)
    latency_token = max(float(latency_ms), 0.0)

    module = _load_native_module()
    if module is not None and hasattr(module, "smart_router_score"):
        try:
            return float(
                module.smart_router_score(
                    spread_token,
                    volume_token,
                    fee_token,
                    slippage_token,
                    fill_token,
                    latency_token,
                )
            )
        except Exception:
            pass

    spread_score = 1.0 / (1.0 + spread_token * 100.0)
    volume_score = min(volume_token / 1_000_000, 1.0)
    fee_score = 1.0 / (1.0 + max(fee_token, -5.0) / 10.0)
    quality_score = (
        (1.0 / slippage_token) * 0.5
        + fill_token * 0.3
        + (1.0 / (1.0 + latency_token / 500.0)) * 0.2
    )
    return float(spread_score * 0.30 + volume_score * 0.30 + fee_score * 0.20 + quality_score * 0.20)


def quote_state(*, price: float, age_seconds: float, stale_after_seconds: float) -> tuple[bool, bool]:
    price_token = float(price)
    age_token = float(age_seconds)
    stale_after = max(float(stale_after_seconds), 0.0)

    module = _load_native_module()
    if module is not None and hasattr(module, "quote_state"):
        try:
            stale, usable = module.quote_state(price_token, age_token, stale_after)
            return bool(stale), bool(usable)
        except Exception:
            pass

    valid_price = price_token > 0.0
    if age_token != age_token:  # NaN guard
        age_token = float("inf")
    stale = max(age_token, 0.0) > stale_after
    return bool(stale), bool(valid_price and not stale)
