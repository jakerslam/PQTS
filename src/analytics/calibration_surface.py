"""Calibration-surface and mispricing diagnostics pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CalibrationObservation:
    market_id: str
    predicted_probability: float
    realized_outcome: float
    regime: str = "unknown"


@dataclass(frozen=True)
class CalibrationBucketRow:
    regime: str
    bucket_label: str
    bucket_low: float
    bucket_high: float
    samples: int
    predicted_avg: float
    realized_rate: float
    calibration_error: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MispricingSignal:
    market_id: str
    regime: str
    posterior_probability: float
    implied_probability: float
    edge: float
    action: str
    conviction: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clip_prob(value: float) -> float:
    return min(max(float(value), 0.0), 1.0)


def _bucket_label(low: float, high: float) -> str:
    return f"[{low:.2f},{high:.2f})"


def _bucket_index(prob: float, edges: list[float]) -> int:
    for idx in range(len(edges) - 1):
        low = edges[idx]
        high = edges[idx + 1]
        if low <= prob < high:
            return idx
    return len(edges) - 2


def build_calibration_surface(
    observations: list[CalibrationObservation],
    *,
    bucket_edges: tuple[float, ...] = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
) -> list[CalibrationBucketRow]:
    if len(bucket_edges) < 2:
        raise ValueError("bucket_edges must include at least two points.")
    edges = [_clip_prob(edge) for edge in bucket_edges]
    if sorted(edges) != edges:
        raise ValueError("bucket_edges must be sorted ascending.")

    grouped: dict[tuple[str, int], list[CalibrationObservation]] = {}
    for row in observations:
        p = _clip_prob(row.predicted_probability)
        idx = _bucket_index(p, edges)
        grouped.setdefault((str(row.regime), idx), []).append(
            CalibrationObservation(
                market_id=str(row.market_id),
                predicted_probability=p,
                realized_outcome=_clip_prob(row.realized_outcome),
                regime=str(row.regime),
            )
        )

    result: list[CalibrationBucketRow] = []
    for (regime, idx), rows in grouped.items():
        low = edges[idx]
        high = edges[idx + 1]
        predicted_avg = sum(item.predicted_probability for item in rows) / float(len(rows))
        realized_rate = sum(item.realized_outcome for item in rows) / float(len(rows))
        result.append(
            CalibrationBucketRow(
                regime=regime,
                bucket_label=_bucket_label(low, high),
                bucket_low=low,
                bucket_high=high,
                samples=len(rows),
                predicted_avg=predicted_avg,
                realized_rate=realized_rate,
                calibration_error=(realized_rate - predicted_avg),
            )
        )
    result.sort(key=lambda row: (row.regime, row.bucket_low, row.bucket_high))
    return result


def diagnose_mispricing(
    *,
    posterior_probabilities: dict[str, float],
    implied_probabilities: dict[str, float],
    regime_by_market: dict[str, str] | None = None,
    min_edge: float = 0.03,
) -> list[MispricingSignal]:
    signals: list[MispricingSignal] = []
    regime_map = dict(regime_by_market or {})
    threshold = abs(float(min_edge))
    for market_id, posterior in posterior_probabilities.items():
        if market_id not in implied_probabilities:
            continue
        post = _clip_prob(float(posterior))
        implied = _clip_prob(float(implied_probabilities[market_id]))
        edge = post - implied
        if abs(edge) < threshold:
            continue
        signals.append(
            MispricingSignal(
                market_id=str(market_id),
                regime=str(regime_map.get(market_id, "unknown")),
                posterior_probability=post,
                implied_probability=implied,
                edge=edge,
                action="buy" if edge > 0 else "sell",
                conviction=abs(edge),
            )
        )
    signals.sort(key=lambda row: row.conviction, reverse=True)
    return signals


def run_calibration_mispricing_pipeline(
    *,
    observations: list[CalibrationObservation],
    posterior_probabilities: dict[str, float],
    implied_probabilities: dict[str, float],
    regime_by_market: dict[str, str] | None = None,
    min_edge: float = 0.03,
) -> dict[str, Any]:
    surface = build_calibration_surface(observations)
    mispricing = diagnose_mispricing(
        posterior_probabilities=posterior_probabilities,
        implied_probabilities=implied_probabilities,
        regime_by_market=regime_by_market,
        min_edge=min_edge,
    )
    return {
        "calibration_surface": [row.to_dict() for row in surface],
        "mispricing_signals": [row.to_dict() for row in mispricing],
        "summary": {
            "surface_rows": len(surface),
            "signals": len(mispricing),
            "regimes": sorted({row["regime"] for row in [item.to_dict() for item in surface]}),
        },
    }
