"""Regime-conditioned exposure throttling for pre-trade quantity control."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class RegimeDecision:
    regime: str
    multiplier: float
    reason: str


class RegimeExposureOverlay:
    """Classify market regime from microstructure and throttle exposure accordingly."""

    def __init__(self, config: Dict | None = None):
        cfg = config or {}
        self.high_spread = float(cfg.get("high_spread", 0.0015))
        self.extreme_spread = float(cfg.get("extreme_spread", 0.004))
        self.low_volume = float(cfg.get("low_volume_24h", 300000.0))
        self.normal_multiplier = float(cfg.get("normal_multiplier", 1.0))
        self.high_vol_multiplier = float(cfg.get("high_vol_multiplier", 0.7))
        self.low_liquidity_multiplier = float(cfg.get("low_liquidity_multiplier", 0.5))
        self.crisis_multiplier = float(cfg.get("crisis_multiplier", 0.25))

    def classify(self, symbol: str, market_data: Dict) -> RegimeDecision:
        spread = 0.0
        volume_24h = float(market_data.get("vol_24h", 0.0) or 0.0)

        for venue_payload in market_data.values():
            if not isinstance(venue_payload, dict):
                continue
            if symbol not in venue_payload:
                continue
            quote = venue_payload[symbol]
            if not isinstance(quote, dict):
                continue
            spread = max(spread, float(quote.get("spread", 0.0) or 0.0))
            volume_24h = max(volume_24h, float(quote.get("volume_24h", 0.0) or 0.0))

        if spread >= self.extreme_spread:
            return RegimeDecision("crisis", self.crisis_multiplier, "extreme_spread")
        if volume_24h > 0 and volume_24h <= self.low_volume:
            return RegimeDecision("low_liquidity", self.low_liquidity_multiplier, "low_volume")
        if spread >= self.high_spread:
            return RegimeDecision("high_vol", self.high_vol_multiplier, "high_spread")
        return RegimeDecision("normal", self.normal_multiplier, "within_limits")

    def throttle_quantity(self, symbol: str, quantity: float, market_data: Dict) -> Tuple[float, RegimeDecision]:
        decision = self.classify(symbol, market_data)
        adjusted = float(quantity) * float(decision.multiplier)
        return max(adjusted, 0.0), decision
