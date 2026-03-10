"""Streamlit↔Next parity checks for key dashboard metrics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@dataclass(frozen=True)
class MetricParityResult:
    key: str
    streamlit_value: float
    web_value: float
    delta: float
    tolerance: float
    within_tolerance: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ParityCheckReport:
    passed: bool
    checked_metrics: int
    mismatches: int
    rows: list[MetricParityResult]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["rows"] = [row.to_dict() for row in self.rows]
        return payload


def compare_dashboard_metrics(
    *,
    streamlit_metrics: Mapping[str, Any],
    web_metrics: Mapping[str, Any],
    metric_keys: Sequence[str],
    default_tolerance: float = 1e-6,
    tolerance_overrides: Mapping[str, float] | None = None,
) -> ParityCheckReport:
    overrides = {str(k): float(v) for k, v in dict(tolerance_overrides or {}).items()}
    rows: list[MetricParityResult] = []
    mismatch_count = 0
    for key in metric_keys:
        token = str(key)
        streamlit_value = _as_float(streamlit_metrics.get(token))
        web_value = _as_float(web_metrics.get(token))
        delta = abs(streamlit_value - web_value)
        tolerance = max(float(overrides.get(token, default_tolerance)), 0.0)
        within = delta <= tolerance
        if not within:
            mismatch_count += 1
        rows.append(
            MetricParityResult(
                key=token,
                streamlit_value=streamlit_value,
                web_value=web_value,
                delta=delta,
                tolerance=tolerance,
                within_tolerance=within,
            )
        )
    return ParityCheckReport(
        passed=mismatch_count == 0,
        checked_metrics=len(rows),
        mismatches=mismatch_count,
        rows=rows,
    )
