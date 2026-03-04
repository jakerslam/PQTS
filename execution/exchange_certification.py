"""Exchange adapter certification harness for sandbox/live-readiness checks."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, Protocol


@dataclass(frozen=True)
class CertificationThresholds:
    max_auth_latency_ms: float = 5000.0
    max_submit_latency_ms: float = 5000.0
    max_cancel_latency_ms: float = 5000.0
    max_reconnect_latency_ms: float = 10000.0


@dataclass(frozen=True)
class CertificationResult:
    venue: str
    passed: bool
    checks: Dict[str, bool]
    latencies_ms: Dict[str, float]
    failures: list[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "venue": self.venue,
            "passed": bool(self.passed),
            "checks": dict(self.checks),
            "latencies_ms": dict(self.latencies_ms),
            "failures": list(self.failures),
        }


class AdapterCertificationProbe(Protocol):
    async def auth_check(self) -> bool: ...

    async def submit_order_check(self) -> bool: ...

    async def cancel_order_check(self) -> bool: ...

    async def partial_fill_check(self) -> bool: ...

    async def reconnect_check(self) -> bool: ...


async def run_adapter_certification(
    *,
    venue: str,
    probe: AdapterCertificationProbe,
    thresholds: CertificationThresholds | None = None,
) -> CertificationResult:
    cfg = thresholds or CertificationThresholds()

    checks: Dict[str, bool] = {}
    latencies_ms: Dict[str, float] = {}

    async def _timed(name: str, fn):
        start = time.perf_counter()
        ok = bool(await fn())
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        checks[name] = ok
        latencies_ms[name] = float(elapsed_ms)

    await _timed("auth", probe.auth_check)
    await _timed("submit_order", probe.submit_order_check)
    await _timed("cancel_order", probe.cancel_order_check)
    await _timed("partial_fill", probe.partial_fill_check)
    await _timed("reconnect", probe.reconnect_check)

    failures: list[str] = []
    if not checks["auth"]:
        failures.append("auth_check_failed")
    if not checks["submit_order"]:
        failures.append("submit_order_check_failed")
    if not checks["cancel_order"]:
        failures.append("cancel_order_check_failed")
    if not checks["partial_fill"]:
        failures.append("partial_fill_check_failed")
    if not checks["reconnect"]:
        failures.append("reconnect_check_failed")

    if latencies_ms["auth"] > cfg.max_auth_latency_ms:
        failures.append("auth_latency_exceeded")
    if latencies_ms["submit_order"] > cfg.max_submit_latency_ms:
        failures.append("submit_latency_exceeded")
    if latencies_ms["cancel_order"] > cfg.max_cancel_latency_ms:
        failures.append("cancel_latency_exceeded")
    if latencies_ms["reconnect"] > cfg.max_reconnect_latency_ms:
        failures.append("reconnect_latency_exceeded")

    return CertificationResult(
        venue=str(venue),
        passed=(len(failures) == 0),
        checks=checks,
        latencies_ms=latencies_ms,
        failures=failures,
    )


def summarize_certification(results: list[CertificationResult]) -> Dict[str, Any]:
    passed = [row for row in results if row.passed]
    failed = [row for row in results if not row.passed]
    return {
        "venues_total": len(results),
        "venues_passed": len(passed),
        "venues_failed": len(failed),
        "all_passed": len(failed) == 0,
        "results": [row.to_dict() for row in results],
    }
