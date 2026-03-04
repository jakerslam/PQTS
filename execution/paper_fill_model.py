"""Deterministic microstructure-aware paper fill provider."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib

from execution.tca_feedback import ExecutionFill


@dataclass(frozen=True)
class PaperFillModelConfig:
    """Configuration for deterministic paper execution simulation."""

    base_latency_ms: float = 35.0
    latency_jitter_ms: float = 45.0
    partial_fill_notional_usd: float = 25000.0
    min_partial_fill_ratio: float = 0.55
    adverse_selection_bps: float = 8.0
    min_slippage_bps: float = 1.0
    reality_stress_mode: bool = False
    stress_slippage_multiplier: float = 2.5
    stress_fill_ratio_multiplier: float = 0.70
    hard_reject_notional_usd: float = 250000.0


class MicrostructurePaperFillProvider:
    """Generate deterministic fills with partial-fill and impact realism."""

    def __init__(self, config: PaperFillModelConfig | None = None):
        self.config = config or PaperFillModelConfig()

    @staticmethod
    def _uniform(*parts: object) -> float:
        payload = "|".join(str(p) for p in parts).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        return int(digest[:8], 16) / float(0xFFFFFFFF)

    def _latency_ms(self, *, order_id: str, symbol: str, venue: str) -> float:
        u = self._uniform(order_id, symbol, venue, "latency")
        return float(self.config.base_latency_ms + (self.config.latency_jitter_ms * u))

    def _fill_ratio(
        self,
        *,
        order_id: str,
        symbol: str,
        venue: str,
        notional: float,
    ) -> float:
        if notional <= self.config.partial_fill_notional_usd:
            return 1.0

        capacity_ratio = self.config.partial_fill_notional_usd / max(notional, 1e-9)
        capacity_ratio = max(min(capacity_ratio, 1.0), self.config.min_partial_fill_ratio)
        u = self._uniform(order_id, symbol, venue, "fill_ratio")
        jitter = 0.9 + (0.2 * u)
        return float(max(min(capacity_ratio * jitter, 1.0), self.config.min_partial_fill_ratio))

    async def get_fill(
        self,
        *,
        order_id: str,
        symbol: str,
        venue: str,
        side: str,
        requested_qty: float,
        reference_price: float,
    ) -> ExecutionFill:
        notional = float(requested_qty) * float(reference_price)
        if notional >= self.config.hard_reject_notional_usd:
            latency_ms = self._latency_ms(order_id=order_id, symbol=symbol, venue=venue)
            timestamp = datetime.now(timezone.utc) + timedelta(milliseconds=latency_ms)
            return ExecutionFill(
                executed_price=float(reference_price),
                executed_qty=0.0,
                timestamp=timestamp,
                venue=venue,
                symbol=symbol,
            )

        fill_ratio = self._fill_ratio(
            order_id=order_id,
            symbol=symbol,
            venue=venue,
            notional=notional,
        )
        if bool(self.config.reality_stress_mode):
            fill_ratio *= float(self.config.stress_fill_ratio_multiplier)
            fill_ratio = float(max(min(fill_ratio, 1.0), 0.0))
        executed_qty = float(requested_qty) * fill_ratio

        impact_scale = max((notional / max(self.config.partial_fill_notional_usd, 1e-9)) - 1.0, 0.0)
        stochastic_component = (self._uniform(order_id, symbol, venue, "slippage") - 0.5) * 0.6
        slip_bps = self.config.adverse_selection_bps * (0.5 + impact_scale) + stochastic_component
        slip_bps = max(float(slip_bps), float(self.config.min_slippage_bps))
        if bool(self.config.reality_stress_mode):
            slip_bps *= float(self.config.stress_slippage_multiplier)

        if str(side).lower() == "buy":
            executed_price = float(reference_price) * (1.0 + (slip_bps / 10000.0))
        else:
            executed_price = float(reference_price) * (1.0 - (slip_bps / 10000.0))

        latency_ms = self._latency_ms(order_id=order_id, symbol=symbol, venue=venue)
        timestamp = datetime.now(timezone.utc) + timedelta(milliseconds=latency_ms)

        return ExecutionFill(
            executed_price=float(executed_price),
            executed_qty=float(executed_qty),
            timestamp=timestamp,
            venue=venue,
            symbol=symbol,
        )
