"""No-look-ahead / leakage validation helpers for strategy submissions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping


def _parse_ts(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value))
    token = str(value).strip()
    if not token:
        raise ValueError("empty timestamp")
    return datetime.fromisoformat(token)


@dataclass(frozen=True)
class LeakageViolation:
    index: int
    feature_ts: str
    target_ts: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": int(self.index),
            "feature_ts": str(self.feature_ts),
            "target_ts": str(self.target_ts),
            "reason": str(self.reason),
        }


def validate_no_lookahead(
    rows: Iterable[Mapping[str, Any]],
    *,
    feature_ts_key: str = "feature_ts",
    target_ts_key: str = "target_ts",
) -> dict[str, Any]:
    violations: list[LeakageViolation] = []
    checked = 0
    for idx, row in enumerate(rows):
        checked += 1
        feature_raw = row.get(feature_ts_key)
        target_raw = row.get(target_ts_key)
        try:
            feature_ts = _parse_ts(feature_raw)
            target_ts = _parse_ts(target_raw)
        except Exception as exc:  # noqa: BLE001
            violations.append(
                LeakageViolation(
                    index=idx,
                    feature_ts=str(feature_raw),
                    target_ts=str(target_raw),
                    reason=f"invalid_timestamp:{exc}",
                )
            )
            continue
        if feature_ts > target_ts:
            violations.append(
                LeakageViolation(
                    index=idx,
                    feature_ts=feature_ts.isoformat(),
                    target_ts=target_ts.isoformat(),
                    reason="feature_timestamp_after_target",
                )
            )
    return {
        "checked_rows": int(checked),
        "violations": [row.to_dict() for row in violations],
        "passed": len(violations) == 0,
    }


def summarize_leakage_report(report: Mapping[str, Any]) -> str:
    checked = int(report.get("checked_rows", 0))
    violations = report.get("violations", [])
    violation_count = len(violations) if isinstance(violations, list) else 0
    passed = bool(report.get("passed", False))
    status = "PASS" if passed else "FAIL"
    return f"{status} no-lookahead validation: checked={checked} violations={violation_count}"
