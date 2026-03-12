"""Adaptive ML / RL / evolutionary training contracts for Studio."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class TrainingArtifact:
    mode: str
    strategy_id: str
    run_id: str
    score: float
    metadata: dict[str, Any]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "strategy_id": self.strategy_id,
            "run_id": self.run_id,
            "score": float(self.score),
            "metadata": dict(self.metadata),
            "generated_at": self.generated_at,
        }


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def run_adaptive_ensemble_training(
    *,
    strategy_id: str,
    candidate_models: Iterable[Mapping[str, Any]],
    retrain_on_live_data: bool,
    optuna_trials: int = 32,
) -> TrainingArtifact:
    scores = [_safe_float(row.get("score"), 0.0) for row in candidate_models]
    baseline = max(scores) if scores else 0.0
    retrain_bonus = 0.02 if bool(retrain_on_live_data) else 0.0
    trial_bonus = min(float(optuna_trials), 256.0) / 2560.0
    score = max(min(baseline + retrain_bonus + trial_bonus, 1.0), -1.0)
    run_id = f"adaptive_{abs(hash((strategy_id, optuna_trials, len(scores)))) % 10_000_000:07d}"
    return TrainingArtifact(
        mode="adaptive_ensemble",
        strategy_id=str(strategy_id),
        run_id=run_id,
        score=score,
        metadata={
            "candidate_count": len(scores),
            "retrain_on_live_data": bool(retrain_on_live_data),
            "optuna_trials": int(optuna_trials),
        },
        generated_at=_utc_now(),
    )


def run_rl_training(
    *,
    strategy_id: str,
    episodes: int = 200,
    reward_mean: float = 0.0,
    reward_std: float = 1.0,
) -> TrainingArtifact:
    stability = max(0.0, 1.0 - abs(_safe_float(reward_std, 1.0)))
    exploration = min(max(float(episodes), 1.0), 10_000.0) / 10_000.0
    score = max(min(_safe_float(reward_mean) * 0.5 + stability * 0.4 + exploration * 0.1, 1.0), -1.0)
    run_id = f"rl_{abs(hash((strategy_id, episodes))) % 10_000_000:07d}"
    return TrainingArtifact(
        mode="rl",
        strategy_id=str(strategy_id),
        run_id=run_id,
        score=score,
        metadata={
            "episodes": int(episodes),
            "reward_mean": float(reward_mean),
            "reward_std": float(reward_std),
        },
        generated_at=_utc_now(),
    )


def run_evolutionary_search(
    *,
    strategy_id: str,
    generations: int = 30,
    population_size: int = 64,
    best_fitness: float = 0.0,
) -> TrainingArtifact:
    breadth = min(max(float(population_size), 4.0), 4096.0) / 4096.0
    depth = min(max(float(generations), 1.0), 1000.0) / 1000.0
    score = max(min(_safe_float(best_fitness) * 0.7 + breadth * 0.15 + depth * 0.15, 1.0), -1.0)
    run_id = f"evo_{abs(hash((strategy_id, generations, population_size))) % 10_000_000:07d}"
    return TrainingArtifact(
        mode="evolutionary",
        strategy_id=str(strategy_id),
        run_id=run_id,
        score=score,
        metadata={
            "generations": int(generations),
            "population_size": int(population_size),
            "best_fitness": float(best_fitness),
        },
        generated_at=_utc_now(),
    )
