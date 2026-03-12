"""Normalized multi-asset instrument contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NormalizedInstrument:
    venue: str
    symbol: str
    asset_class: str
    base_asset: str
    quote_asset: str
    contract_type: str = "spot"
    expiry: str = ""
    strike: float | None = None
    option_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "venue": self.venue,
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "base_asset": self.base_asset,
            "quote_asset": self.quote_asset,
            "contract_type": self.contract_type,
            "expiry": self.expiry,
            "strike": self.strike,
            "option_type": self.option_type,
        }


def normalize_instrument(*, venue: str, symbol: str, market: str = "crypto") -> NormalizedInstrument:
    market_token = str(market).strip().lower()
    symbol_token = str(symbol).strip()
    venue_token = str(venue).strip().lower()
    if market_token == "forex":
        if "/" in symbol_token:
            base, quote = symbol_token.split("/", 1)
        elif "-" in symbol_token:
            base, quote = symbol_token.split("-", 1)
        else:
            base, quote = symbol_token[:3], symbol_token[3:]
        return NormalizedInstrument(
            venue=venue_token,
            symbol=symbol_token,
            asset_class="forex",
            base_asset=base.upper(),
            quote_asset=quote.upper(),
            contract_type="spot",
        )
    if market_token == "equities":
        return NormalizedInstrument(
            venue=venue_token,
            symbol=symbol_token.upper(),
            asset_class="equities",
            base_asset=symbol_token.upper(),
            quote_asset="USD",
            contract_type="spot",
        )
    if market_token == "futures":
        base = symbol_token.split("-")[0].upper()
        return NormalizedInstrument(
            venue=venue_token,
            symbol=symbol_token.upper(),
            asset_class="futures",
            base_asset=base,
            quote_asset="USD",
            contract_type="future",
        )
    if market_token == "options":
        base = symbol_token.split("-")[0].upper()
        option_type = "call" if "C" in symbol_token.upper() else ("put" if "P" in symbol_token.upper() else "")
        return NormalizedInstrument(
            venue=venue_token,
            symbol=symbol_token.upper(),
            asset_class="options",
            base_asset=base,
            quote_asset="USD",
            contract_type="option",
            option_type=option_type,
        )

    if "-" in symbol_token:
        base, quote = symbol_token.split("-", 1)
    elif "/" in symbol_token:
        base, quote = symbol_token.split("/", 1)
    else:
        base, quote = symbol_token[:3], symbol_token[3:]
    contract_type = "perpetual" if any(tag in symbol_token.upper() for tag in ("PERP", "SWAP")) else "spot"
    return NormalizedInstrument(
        venue=venue_token,
        symbol=symbol_token.upper(),
        asset_class="crypto",
        base_asset=base.upper(),
        quote_asset=quote.upper(),
        contract_type=contract_type,
    )
