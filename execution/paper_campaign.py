"""Helpers for continuous paper-trading campaign orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple

from execution.smart_router import OrderRequest, OrderType


@dataclass
class CampaignStats:
    submitted: int = 0
    filled: int = 0
    rejected: int = 0

    @property
    def reject_rate(self) -> float:
        return float(self.rejected / max(self.submitted, 1))


def build_portfolio_snapshot(
    *,
    positions: Dict[str, float],
    prices: Dict[str, float],
    capital: float,
    total_pnl: float = 0.0,
    realized_pnl: float = 0.0,
    unrealized_pnl: float = 0.0,
) -> Dict[str, Any]:
    gross = 0.0
    net = 0.0
    for symbol, qty in positions.items():
        px = float(prices.get(symbol, 0.0))
        exposure = float(qty) * px
        gross += abs(exposure)
        net += exposure

    leverage = gross / max(float(capital), 1e-9)
    return {
        "positions": dict(positions),
        "prices": dict(prices),
        "total_pnl": float(total_pnl),
        "unrealized_pnl": float(unrealized_pnl),
        "realized_pnl": float(realized_pnl),
        "gross_exposure": float(gross),
        "net_exposure": float(net),
        "leverage": float(leverage),
        "open_orders": [],
    }


def select_symbol_price(snapshot: Dict[str, Any], symbol: str) -> Optional[Tuple[str, float]]:
    for venue, payload in snapshot.items():
        if venue in {"order_book", "last_price", "vol_24h"}:
            continue
        if not isinstance(payload, dict):
            continue
        quote = payload.get(symbol)
        if not isinstance(quote, dict):
            continue
        price = float(quote.get("price", 0.0) or 0.0)
        if price > 0:
            return venue, price
    return None


def build_probe_order(
    *,
    symbol: str,
    side: str,
    notional_usd: float,
    price: float,
    order_type: OrderType = OrderType.LIMIT,
    strategy_id: str = "campaign",
    expected_alpha_bps: float = 0.0,
) -> OrderRequest:
    quantity = float(notional_usd) / max(float(price), 1e-9)
    return OrderRequest(
        symbol=symbol,
        side=side,
        quantity=float(quantity),
        order_type=order_type,
        price=float(price) if order_type == OrderType.LIMIT else None,
        strategy_id=str(strategy_id or "campaign"),
        expected_alpha_bps=float(expected_alpha_bps),
    )


def iter_cycle_symbols(symbols: Iterable[str]) -> list[str]:
    ordered = [str(s).strip() for s in symbols if str(s).strip()]
    if not ordered:
        raise ValueError("At least one symbol is required for paper campaign")
    return ordered
