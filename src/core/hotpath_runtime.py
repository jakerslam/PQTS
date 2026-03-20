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
        "book_metrics",
        "fill_metrics",
        "sequence_transition",
        "uniform_from_seed",
        "event_id_hash",
        "paper_fill_metrics",
        "smart_router_score",
        "quote_state",
        "profitability_net_alpha_bps",
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


def book_metrics(
    bids: Iterable[Any],
    asks: Iterable[Any],
    *,
    max_levels: int = 5,
) -> tuple[float, float, float, float, float, float]:
    normalized_bids = _normalize_levels(bids, max_levels=max_levels)
    normalized_asks = _normalize_levels(asks, max_levels=max_levels)
    module = _load_native_module()
    if module is not None and hasattr(module, "book_metrics"):
        try:
            mid, spread_bps, bid_depth, ask_depth, top_bid_qty, top_ask_qty = module.book_metrics(
                normalized_bids,
                normalized_asks,
                int(max(int(max_levels), 1)),
            )
            return (
                float(mid),
                float(spread_bps),
                float(bid_depth),
                float(ask_depth),
                float(top_bid_qty),
                float(top_ask_qty),
            )
        except Exception:
            pass

    best_bid = normalized_bids[0][0] if normalized_bids else 0.0
    best_ask = normalized_asks[0][0] if normalized_asks else 0.0
    top_bid_qty = normalized_bids[0][1] if normalized_bids else 0.0
    top_ask_qty = normalized_asks[0][1] if normalized_asks else 0.0
    mid = max((best_bid + best_ask) / 2.0, 1e-9) if best_bid > 0.0 and best_ask > 0.0 else 1e-9
    spread_bps = ((best_ask - best_bid) / mid) * 10000.0 if best_bid > 0.0 and best_ask > 0.0 else 0.0
    bid_depth = sum(price * size for price, size in normalized_bids)
    ask_depth = sum(price * size for price, size in normalized_asks)
    return float(mid), float(spread_bps), float(bid_depth), float(ask_depth), float(top_bid_qty), float(top_ask_qty)


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
            fill_ratio, slip_bps, executed_qty, executed_price, queue_turnover = (
                module.paper_fill_metrics(
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
    return float(
        spread_score * 0.30 + volume_score * 0.30 + fee_score * 0.20 + quality_score * 0.20
    )


def quote_state(
    *, price: float, age_seconds: float, stale_after_seconds: float
) -> tuple[bool, bool]:
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


def profitability_net_alpha_bps(
    *,
    expected_alpha_bps: float,
    expected_cost_usd: float,
    expected_slippage_usd: float,
    notional_usd: float,
    min_edge_bps: float,
) -> tuple[float, float, float]:
    """
    Return `(predicted_total_router_bps, predicted_net_alpha_bps, required_alpha_bps)`.
    """
    expected_alpha = float(expected_alpha_bps)
    cost_usd = float(expected_cost_usd)
    slip_usd = float(expected_slippage_usd)
    notional = max(float(notional_usd), 1e-12)
    min_edge = max(float(min_edge_bps), 0.0)

    module = _load_native_module()
    if module is not None and hasattr(module, "profitability_net_alpha_bps"):
        try:
            out = module.profitability_net_alpha_bps(
                expected_alpha,
                cost_usd,
                slip_usd,
                notional,
                min_edge,
            )
            return float(out[0]), float(out[1]), float(out[2])
        except Exception:
            pass

    predicted_total_router_bps = ((cost_usd + slip_usd) / notional) * 10000.0
    predicted_net_alpha_bps = expected_alpha - predicted_total_router_bps
    required_alpha_bps = predicted_total_router_bps + min_edge
    return (
        float(predicted_total_router_bps),
        float(predicted_net_alpha_bps),
        float(required_alpha_bps),
    )


def append_lines(path: str, lines: Iterable[str]) -> int:
    path_token = str(path).strip()
    encoded_lines = [str(line) for line in lines]
    if not path_token or not encoded_lines:
        return 0
    module = _load_native_module()
    if module is not None and hasattr(module, "append_lines"):
        try:
            return int(module.append_lines(path_token, encoded_lines))
        except Exception:
            pass
    with open(path_token, "a", encoding="utf-8") as handle:
        for line in encoded_lines:
            handle.write(f"{line}\n")
    return len(encoded_lines)


def encode_csv_line(fields: Iterable[Any]) -> str:
    values = ["" if item is None else str(item) for item in fields]
    module = _load_native_module()
    if module is not None and hasattr(module, "encode_csv_line"):
        try:
            return str(module.encode_csv_line(values))
        except Exception:
            pass

    out: list[str] = []
    for value in values:
        token = str(value)
        if any(ch in token for ch in [",", '"', "\n", "\r"]):
            token = token.replace('"', '""')
            token = f'"{token}"'
        out.append(token)
    return ",".join(out)


def vector_mean(values: Iterable[float]) -> float:
    payload = [float(v) for v in values]
    module = _load_native_module()
    if module is not None and hasattr(module, "vector_mean"):
        try:
            return float(module.vector_mean(payload))
        except Exception:
            pass
    if not payload:
        return 0.0
    return float(sum(payload) / len(payload))


def vector_percentile(values: Iterable[float], percentile: float) -> float:
    payload = [float(v) for v in values]
    q = float(percentile)
    module = _load_native_module()
    if module is not None and hasattr(module, "vector_percentile"):
        try:
            return float(module.vector_percentile(payload, q))
        except Exception:
            pass
    if not payload:
        return 0.0
    payload = sorted(payload)
    q = max(0.0, min(q, 100.0)) / 100.0
    idx = q * (len(payload) - 1)
    low = int(idx)
    high = min(low + 1, len(payload) - 1)
    if low == high:
        return float(payload[low])
    frac = idx - low
    return float(payload[low] + (payload[high] - payload[low]) * frac)


def reliability_metrics(
    *,
    latencies_ms: Iterable[float],
    rejected_flags: Iterable[float],
    failure_flags: Iterable[float],
) -> tuple[float, float, float, float]:
    lat = [float(v) for v in latencies_ms]
    rej = [float(v) for v in rejected_flags]
    fail = [float(v) for v in failure_flags]
    module = _load_native_module()
    if module is not None and hasattr(module, "reliability_metrics"):
        try:
            samples, p95, rej_rate, fail_rate = module.reliability_metrics(lat, rej, fail)
            return float(samples), float(p95), float(rej_rate), float(fail_rate)
        except Exception:
            pass
    return (
        float(len(lat)),
        float(vector_percentile(lat, 95.0)),
        float(vector_mean(rej)),
        float(vector_mean(fail)),
    )


def pairwise_abs_corr_mean(
    *,
    series: Iterable[Iterable[float]],
    min_len: int = 20,
) -> float:
    payload: list[list[float]] = [[float(v) for v in row] for row in series]
    module = _load_native_module()
    if module is not None and hasattr(module, "pairwise_abs_corr_mean"):
        try:
            return float(module.pairwise_abs_corr_mean(payload, int(max(min_len, 2))))
        except Exception:
            pass
    if len(payload) < 2:
        return 0.0
    corr_values: list[float] = []
    for idx, lhs in enumerate(payload):
        for rhs in payload[idx + 1 :]:
            size = min(len(lhs), len(rhs))
            if size < max(int(min_len), 2):
                continue
            x = lhs[-size:]
            y = rhs[-size:]
            x_mean = sum(x) / size
            y_mean = sum(y) / size
            cov = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y, strict=True))
            x_var = sum((a - x_mean) ** 2 for a in x)
            y_var = sum((b - y_mean) ** 2 for b in y)
            if x_var <= 1e-12 or y_var <= 1e-12:
                continue
            corr_values.append(abs(cov / ((x_var ** 0.5) * (y_var ** 0.5))))
    return float(sum(corr_values) / len(corr_values)) if corr_values else 0.0
