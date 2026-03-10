"""Typed contract between analysis and execution planes for short-cycle paths."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

REQUIRED_FACTORS = (
    "price_vs_target",
    "momentum",
    "volatility",
    "contract_mispricing",
    "futures_sentiment",
    "time_decay",
)


@dataclass(frozen=True)
class AnalysisPayload:
    schema_version: int
    decision_id: str
    strategy_id: str
    asset: str
    interval: str
    generated_at_ms: int
    factors: Mapping[str, float]
    confidence: float
    requested_kelly_fraction: float

    def validate(
        self,
        *,
        now_ms: int,
        expected_schema_version: int = 1,
        max_age_ms: int = 1_000,
    ) -> tuple[bool, tuple[str, ...]]:
        errors: list[str] = []
        if self.schema_version != expected_schema_version:
            errors.append("schema_version_mismatch")
        if now_ms - int(self.generated_at_ms) > max_age_ms:
            errors.append("stale_payload")
        missing = [name for name in REQUIRED_FACTORS if name not in self.factors]
        if missing:
            errors.append(f"missing_factors:{','.join(missing)}")
        if not 0.0 <= float(self.confidence) <= 1.0:
            errors.append("confidence_out_of_range")
        if not 0.0 <= float(self.requested_kelly_fraction) <= 1.0:
            errors.append("kelly_fraction_out_of_range")
        return (not errors, tuple(errors))

    def to_execution_instruction(self) -> dict[str, object]:
        score = float(sum(float(v) for v in self.factors.values()))
        return {
            "decision_id": self.decision_id,
            "strategy_id": self.strategy_id,
            "asset": self.asset,
            "interval": self.interval,
            "score": score,
            "confidence": float(self.confidence),
            "requested_kelly_fraction": float(self.requested_kelly_fraction),
            "analysis_generated_at_ms": int(self.generated_at_ms),
        }


def analysis_to_execution(
    payload: AnalysisPayload,
    *,
    now_ms: int,
    expected_schema_version: int = 1,
    max_age_ms: int = 1_000,
) -> tuple[bool, dict[str, object] | None, tuple[str, ...]]:
    valid, errors = payload.validate(
        now_ms=now_ms,
        expected_schema_version=expected_schema_version,
        max_age_ms=max_age_ms,
    )
    if not valid:
        return False, None, errors
    return True, payload.to_execution_instruction(), ()
