"""Latency and throughput monitors for short-cycle execution governance."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import ceil


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    rank = int(ceil(q * len(values))) - 1
    rank = max(0, min(rank, len(values) - 1))
    return sorted(values)[rank]


@dataclass(frozen=True)
class HFTSLOBudget:
    p95_submit_to_ack_ms: float = 50.0
    p99_submit_to_ack_ms: float = 100.0
    max_reject_rate: float = 0.05
    max_timeout_rate: float = 0.02
    max_decision_to_submit_ms: float = 20.0
    max_orders_per_minute: int = 120
    max_cancel_replace_per_minute: int = 240


class HFTPathMonitor:
    def __init__(self, budget: HFTSLOBudget | None = None) -> None:
        self.budget = budget or HFTSLOBudget()
        self.submit_to_ack_ms: deque[float] = deque(maxlen=5_000)
        self.decision_to_submit_ms: deque[float] = deque(maxlen=5_000)
        self.rejections: deque[bool] = deque(maxlen=5_000)
        self.timeouts: deque[bool] = deque(maxlen=5_000)
        self.order_activity_ts_ms: deque[int] = deque()
        self.cancel_replace_ts_ms: deque[int] = deque()

    def record(
        self,
        *,
        submit_to_ack_ms: float,
        decision_to_submit_ms: float,
        rejected: bool = False,
        timeout: bool = False,
        timestamp_ms: int,
        cancel_replace: bool = False,
    ) -> None:
        self.submit_to_ack_ms.append(float(submit_to_ack_ms))
        self.decision_to_submit_ms.append(float(decision_to_submit_ms))
        self.rejections.append(bool(rejected))
        self.timeouts.append(bool(timeout))
        self.order_activity_ts_ms.append(int(timestamp_ms))
        if cancel_replace:
            self.cancel_replace_ts_ms.append(int(timestamp_ms))
        self._gc(now_ms=timestamp_ms)

    def _gc(self, *, now_ms: int) -> None:
        one_min_ago = now_ms - 60_000
        while self.order_activity_ts_ms and self.order_activity_ts_ms[0] < one_min_ago:
            self.order_activity_ts_ms.popleft()
        while self.cancel_replace_ts_ms and self.cancel_replace_ts_ms[0] < one_min_ago:
            self.cancel_replace_ts_ms.popleft()

    def summary(self) -> dict[str, float]:
        samples = max(len(self.submit_to_ack_ms), 1)
        reject_rate = sum(1 for flag in self.rejections if flag) / samples
        timeout_rate = sum(1 for flag in self.timeouts if flag) / samples
        return {
            "samples": float(len(self.submit_to_ack_ms)),
            "p95_submit_to_ack_ms": _percentile(list(self.submit_to_ack_ms), 0.95),
            "p99_submit_to_ack_ms": _percentile(list(self.submit_to_ack_ms), 0.99),
            "decision_to_submit_max_ms": max(self.decision_to_submit_ms) if self.decision_to_submit_ms else 0.0,
            "reject_rate": reject_rate,
            "timeout_rate": timeout_rate,
            "orders_per_minute": float(len(self.order_activity_ts_ms)),
            "cancel_replace_per_minute": float(len(self.cancel_replace_ts_ms)),
        }

    def should_auto_disable(self) -> tuple[bool, tuple[str, ...]]:
        metrics = self.summary()
        reasons: list[str] = []
        if metrics["p95_submit_to_ack_ms"] > self.budget.p95_submit_to_ack_ms:
            reasons.append("p95_submit_to_ack_slo_breach")
        if metrics["p99_submit_to_ack_ms"] > self.budget.p99_submit_to_ack_ms:
            reasons.append("p99_submit_to_ack_slo_breach")
        if metrics["decision_to_submit_max_ms"] > self.budget.max_decision_to_submit_ms:
            reasons.append("decision_to_submit_slo_breach")
        if metrics["reject_rate"] > self.budget.max_reject_rate:
            reasons.append("reject_rate_breach")
        if metrics["timeout_rate"] > self.budget.max_timeout_rate:
            reasons.append("timeout_rate_breach")
        if metrics["orders_per_minute"] > self.budget.max_orders_per_minute:
            reasons.append("orders_per_minute_breach")
        if metrics["cancel_replace_per_minute"] > self.budget.max_cancel_replace_per_minute:
            reasons.append("cancel_replace_breach")
        return (not reasons, tuple(reasons))
