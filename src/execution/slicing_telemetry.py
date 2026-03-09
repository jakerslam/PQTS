"""VWAP/TWAP/depth-aware execution slicing and fill-quality telemetry."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ExecutionSlice:
    order_id: str
    slice_index: int
    total_slices: int
    quantity: float
    delay_seconds: float
    mode: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FillEvent:
    order_id: str
    timestamp: datetime
    quantity: float
    expected_price: float
    fill_price: float


@dataclass(frozen=True)
class ExecutionTelemetry:
    order_id: str
    total_quantity: float
    filled_quantity: float
    average_expected_price: float
    average_fill_price: float
    slippage_bps: float
    time_to_fill_seconds: float
    fill_ratio: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExecutionSlicer:
    """Generate deterministic execution slices for different execution styles."""

    def __init__(
        self,
        *,
        max_participation: float = 0.05,
        default_slice_delay_seconds: float = 10.0,
    ) -> None:
        self.max_participation = max(float(max_participation), 1e-4)
        self.default_slice_delay_seconds = max(float(default_slice_delay_seconds), 0.0)

    def _equal_slices(self, quantity: float, total_slices: int) -> list[float]:
        total = max(int(total_slices), 1)
        base = float(quantity) / float(total)
        return [base for _ in range(total)]

    def plan_twap(self, *, order_id: str, quantity: float, intervals: int) -> list[ExecutionSlice]:
        amounts = self._equal_slices(quantity, intervals)
        return [
            ExecutionSlice(
                order_id=order_id,
                slice_index=idx + 1,
                total_slices=len(amounts),
                quantity=amount,
                delay_seconds=self.default_slice_delay_seconds,
                mode="twap",
                metadata={},
            )
            for idx, amount in enumerate(amounts)
        ]

    def plan_vwap(
        self,
        *,
        order_id: str,
        quantity: float,
        volume_profile: list[float],
    ) -> list[ExecutionSlice]:
        if not volume_profile:
            return self.plan_twap(order_id=order_id, quantity=quantity, intervals=1)
        weights = [max(float(item), 0.0) for item in volume_profile]
        total_weight = sum(weights)
        if total_weight <= 0:
            return self.plan_twap(order_id=order_id, quantity=quantity, intervals=len(weights))
        amounts = [float(quantity) * (weight / total_weight) for weight in weights]
        return [
            ExecutionSlice(
                order_id=order_id,
                slice_index=idx + 1,
                total_slices=len(amounts),
                quantity=amount,
                delay_seconds=self.default_slice_delay_seconds,
                mode="vwap",
                metadata={"weight": weights[idx]},
            )
            for idx, amount in enumerate(amounts)
        ]

    def plan_depth_aware(
        self,
        *,
        order_id: str,
        quantity: float,
        depth_quantity: float,
    ) -> list[ExecutionSlice]:
        depth = max(float(depth_quantity), 1e-9)
        max_slice = max(depth * float(self.max_participation), 1e-9)
        slices = max(int((float(quantity) / max_slice) + 0.999999), 1)
        amounts = self._equal_slices(quantity, slices)
        return [
            ExecutionSlice(
                order_id=order_id,
                slice_index=idx + 1,
                total_slices=len(amounts),
                quantity=amount,
                delay_seconds=self.default_slice_delay_seconds,
                mode="depth_aware",
                metadata={
                    "depth_quantity": depth,
                    "max_participation": float(self.max_participation),
                },
            )
            for idx, amount in enumerate(amounts)
        ]


class ExecutionQualityTelemetry:
    """Track slippage and time-to-fill metrics by order."""

    def __init__(self) -> None:
        self._events: dict[str, list[FillEvent]] = {}
        self._starts: dict[str, datetime] = {}

    def start_order(self, order_id: str, *, timestamp: datetime | None = None) -> None:
        self._starts[str(order_id)] = timestamp or _utc_now()
        self._events.setdefault(str(order_id), [])

    def record_fill(
        self,
        *,
        order_id: str,
        quantity: float,
        expected_price: float,
        fill_price: float,
        timestamp: datetime | None = None,
    ) -> None:
        key = str(order_id)
        self._events.setdefault(key, []).append(
            FillEvent(
                order_id=key,
                timestamp=timestamp or _utc_now(),
                quantity=float(quantity),
                expected_price=float(expected_price),
                fill_price=float(fill_price),
            )
        )

    def summarize(self, order_id: str, *, target_quantity: float) -> ExecutionTelemetry:
        key = str(order_id)
        rows = list(self._events.get(key, []))
        if not rows:
            return ExecutionTelemetry(
                order_id=key,
                total_quantity=float(target_quantity),
                filled_quantity=0.0,
                average_expected_price=0.0,
                average_fill_price=0.0,
                slippage_bps=0.0,
                time_to_fill_seconds=0.0,
                fill_ratio=0.0,
            )

        filled_qty = sum(item.quantity for item in rows)
        expected_notional = sum(item.expected_price * item.quantity for item in rows)
        fill_notional = sum(item.fill_price * item.quantity for item in rows)
        avg_expected = expected_notional / max(filled_qty, 1e-9)
        avg_fill = fill_notional / max(filled_qty, 1e-9)
        slippage_bps = ((avg_fill - avg_expected) / max(avg_expected, 1e-9)) * 10000.0

        start = self._starts.get(key, rows[0].timestamp)
        end = max(item.timestamp for item in rows)
        time_to_fill = max((end - start).total_seconds(), 0.0)
        target = max(float(target_quantity), 1e-9)
        return ExecutionTelemetry(
            order_id=key,
            total_quantity=float(target_quantity),
            filled_quantity=filled_qty,
            average_expected_price=avg_expected,
            average_fill_price=avg_fill,
            slippage_bps=slippage_bps,
            time_to_fill_seconds=time_to_fill,
            fill_ratio=filled_qty / target,
        )
