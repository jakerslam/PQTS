"""Edge-decay monitor for event-intel strategies under latency/load stress."""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Any


@dataclass(frozen=True)
class EdgeObservation:
    latency_ms: float
    concurrent_load: int
    realized_edge_bps: float


@dataclass
class EdgeDecayMonitor:
    low_load_max: int = 5
    high_load_min: int = 20
    min_samples_per_bucket: int = 3
    decay_tighten_threshold: float = 0.35
    decay_pause_threshold: float = 0.60
    observations: list[EdgeObservation] = field(default_factory=list)

    def record(self, *, latency_ms: float, concurrent_load: int, realized_edge_bps: float) -> None:
        self.observations.append(
            EdgeObservation(
                latency_ms=float(latency_ms),
                concurrent_load=int(concurrent_load),
                realized_edge_bps=float(realized_edge_bps),
            )
        )

    def decision(self) -> dict[str, Any]:
        baseline = [x.realized_edge_bps for x in self.observations if x.concurrent_load <= self.low_load_max]
        stressed = [x.realized_edge_bps for x in self.observations if x.concurrent_load >= self.high_load_min]

        if len(baseline) < self.min_samples_per_bucket or len(stressed) < self.min_samples_per_bucket:
            return {
                "action": "hold",
                "reason": "insufficient_samples",
                "baseline_edge_bps": float(mean(baseline)) if baseline else 0.0,
                "stressed_edge_bps": float(mean(stressed)) if stressed else 0.0,
                "decay_pct": 0.0,
                "recommended_concurrency_scale": 1.0,
            }

        baseline_edge = float(mean(baseline))
        stressed_edge = float(mean(stressed))
        if baseline_edge <= 0.0:
            return {
                "action": "hold",
                "reason": "non_positive_baseline_edge",
                "baseline_edge_bps": baseline_edge,
                "stressed_edge_bps": stressed_edge,
                "decay_pct": 0.0,
                "recommended_concurrency_scale": 1.0,
            }

        decay_pct = max(0.0, (baseline_edge - stressed_edge) / abs(baseline_edge))
        if decay_pct >= self.decay_pause_threshold:
            action = "pause"
            scale = 0.0
        elif decay_pct >= self.decay_tighten_threshold:
            action = "tighten"
            scale = 0.5
        else:
            action = "hold"
            scale = 1.0
        return {
            "action": action,
            "reason": "edge_decay_evaluated",
            "baseline_edge_bps": baseline_edge,
            "stressed_edge_bps": stressed_edge,
            "decay_pct": decay_pct,
            "recommended_concurrency_scale": scale,
        }
