"""Polymarket MCP-style tool catalog and execution helpers."""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence


def _now_ts() -> float:
    return float(time.time())


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


@dataclass
class MCPError(Exception):
    tool: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"tool": self.tool, "message": self.message, "context": dict(self.context)}


@dataclass(frozen=True)
class MCPTool:
    name: str
    description: str
    params_schema: dict[str, Any]


@dataclass(frozen=True)
class Market:
    market_id: str
    question: str
    tags: tuple[str, ...] = ()
    status: str = "active"
    close_time: float | None = None
    volume_24h: float = 0.0
    volume_7d: float = 0.0
    volume_30d: float = 0.0
    liquidity: float = 0.0
    yes_price: float = 0.0
    no_price: float = 0.0
    price_change_24h: float = 0.0


@dataclass(frozen=True)
class Order:
    order_id: str
    market_id: str
    side: str
    price: float
    size: float
    status: str
    created_at: float


@dataclass(frozen=True)
class Position:
    market_id: str
    side: str
    size: float
    entry_price: float
    mark_price: float


@dataclass(frozen=True)
class PortfolioState:
    positions: list[Position]
    realized_pnl: float
    unrealized_pnl: float
    portfolio_value: float
    updated_at: float


@dataclass(frozen=True)
class RiskLimits:
    max_order_size: float = 100.0
    max_total_exposure: float = 1000.0
    max_position_per_market: float = 200.0
    min_liquidity: float = 50.0
    max_spread: float = 0.1
    large_order_threshold: float = 250.0


@dataclass(frozen=True)
class AuthConfig:
    mode: str = "l2"
    wallet_address: str = ""
    api_key: str = ""
    api_secret: str = ""


@dataclass
class TokenBucket:
    capacity: int
    refill_rate: float
    tokens: float = field(init=False)
    last_ts: float = field(default_factory=_now_ts)

    def __post_init__(self) -> None:
        self.tokens = float(self.capacity)

    def allow(self, amount: float = 1.0) -> bool:
        now = _now_ts()
        elapsed = max(0.0, now - self.last_ts)
        self.tokens = min(float(self.capacity), self.tokens + elapsed * self.refill_rate)
        self.last_ts = now
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False


class PolymarketClient:
    """In-memory client interface for tests and local flows."""

    def __init__(self, markets: Sequence[Market] | None = None) -> None:
        self._markets = list(markets or [])
        self._orders: list[Order] = []
        self._positions: list[Position] = []

    def list_markets(self) -> list[Market]:
        return list(self._markets)

    def get_market(self, market_id: str) -> Market | None:
        for market in self._markets:
            if market.market_id == market_id:
                return market
        return None

    def add_order(self, order: Order) -> None:
        self._orders.append(order)

    def list_orders(self) -> list[Order]:
        return list(self._orders)

    def cancel_orders(self, order_ids: Iterable[str]) -> int:
        before = len(self._orders)
        self._orders = [o for o in self._orders if o.order_id not in set(order_ids)]
        return before - len(self._orders)

    def set_positions(self, positions: Sequence[Position]) -> None:
        self._positions = list(positions)

    def list_positions(self) -> list[Position]:
        return list(self._positions)


class PolymarketMCPServer:
    def __init__(
        self,
        *,
        client: PolymarketClient,
        router: Any,
        risk_limits: RiskLimits | None = None,
        auth: AuthConfig | None = None,
    ) -> None:
        self.client = client
        self.router = router
        self.risk_limits = risk_limits or RiskLimits()
        self.auth = auth or AuthConfig()
        self.rate_limits: dict[str, TokenBucket] = {
            "discovery": TokenBucket(20, 0.5),
            "analysis": TokenBucket(30, 1.0),
            "trading": TokenBucket(10, 0.2),
            "portfolio": TokenBucket(15, 0.3),
            "websocket": TokenBucket(5, 0.1),
        }

    def list_tools(self) -> list[MCPTool]:
        return [
            MCPTool("market_search", "Search markets by keyword", {"query": "string"}),
            MCPTool("market_trending", "Trending markets by volume window", {"window": "24h|7d|30d"}),
            MCPTool("market_category", "Filter markets by category tag", {"tag": "string"}),
            MCPTool("market_closing_soon", "Markets closing soon", {"hours": "number"}),
            MCPTool("market_featured", "Featured markets", {}),
            MCPTool("market_sports", "Sports markets", {}),
            MCPTool("market_crypto", "Crypto markets", {}),
            MCPTool("market_details", "Market details", {"market_id": "string"}),
            MCPTool("market_orderbook", "Orderbook depth", {"market_id": "string"}),
            MCPTool("market_spread", "Spread and liquidity metrics", {"market_id": "string"}),
            MCPTool("opportunity_analyze", "Opportunity analysis", {"market_id": "string"}),
            MCPTool("market_compare", "Compare markets", {"market_ids": "list"}),
            MCPTool("order_place", "Place order", {"market_id": "string", "side": "yes|no", "price": "number", "size": "number"}),
            MCPTool("order_cancel", "Cancel order", {"order_id": "string"}),
            MCPTool("order_open", "List open orders", {}),
            MCPTool("order_history", "List order history", {}),
            MCPTool("order_batch", "Batch submit orders", {"orders": "list"}),
            MCPTool("order_cancel_all", "Cancel all orders", {}),
            MCPTool("portfolio_state", "Portfolio telemetry", {}),
            MCPTool("portfolio_rebalance", "Rebalance positions", {"targets": "list"}),
        ]

    def _rate_limit(self, category: str) -> None:
        bucket = self.rate_limits.get(category)
        if bucket and not bucket.allow():
            raise MCPError(tool="rate_limit", message="rate_limited", context={"category": category})

    def _require_auth(self) -> None:
        if not str(self.auth.wallet_address).strip():
            raise MCPError(tool="auth", message="wallet_missing")

    def _validate_trade(self, market: Market, size: float, price: float) -> None:
        if size <= 0 or price <= 0:
            raise MCPError(tool="pre_trade", message="invalid_size_or_price")
        if size > self.risk_limits.max_order_size:
            raise MCPError(tool="pre_trade", message="max_order_size_exceeded")
        if market.liquidity < self.risk_limits.min_liquidity:
            raise MCPError(tool="pre_trade", message="insufficient_liquidity")
        spread = abs(market.yes_price - market.no_price)
        if spread > self.risk_limits.max_spread:
            raise MCPError(tool="pre_trade", message="spread_too_wide")

    def search_markets(self, query: str) -> list[Market]:
        self._rate_limit("discovery")
        tokens = set(str(query).lower().split())
        return [
            market
            for market in self.client.list_markets()
            if tokens.intersection(set(market.question.lower().split()))
        ]

    def trending_markets(self, window: str = "24h") -> list[Market]:
        self._rate_limit("discovery")
        key = "volume_24h" if window == "24h" else "volume_7d" if window == "7d" else "volume_30d"
        return sorted(self.client.list_markets(), key=lambda m: getattr(m, key), reverse=True)

    def category_markets(self, tag: str) -> list[Market]:
        self._rate_limit("discovery")
        return [market for market in self.client.list_markets() if tag in market.tags]

    def closing_soon(self, hours: float = 24.0) -> list[Market]:
        self._rate_limit("discovery")
        cutoff = _now_ts() + float(hours) * 3600.0
        return [market for market in self.client.list_markets() if market.close_time and market.close_time <= cutoff]

    def featured(self) -> list[Market]:
        self._rate_limit("discovery")
        return [market for market in self.client.list_markets() if "featured" in market.tags]

    def sports(self) -> list[Market]:
        self._rate_limit("discovery")
        return [market for market in self.client.list_markets() if "sports" in market.tags]

    def crypto(self) -> list[Market]:
        self._rate_limit("discovery")
        return [market for market in self.client.list_markets() if "crypto" in market.tags]

    def market_details(self, market_id: str) -> Market:
        self._rate_limit("analysis")
        market = self.client.get_market(market_id)
        if not market:
            raise MCPError(tool="market_details", message="market_not_found", context={"market_id": market_id})
        return market

    def market_spread(self, market_id: str) -> dict[str, Any]:
        market = self.market_details(market_id)
        spread = abs(market.yes_price - market.no_price)
        return {
            "market_id": market.market_id,
            "spread": spread,
            "liquidity": market.liquidity,
            "timestamp": _now_ts(),
        }

    def opportunity_analysis(self, market_id: str) -> dict[str, Any]:
        market = self.market_details(market_id)
        competitiveness = 1.0 - abs(market.yes_price - market.no_price)
        confidence = min(1.0, competitiveness + math.log1p(market.liquidity) / 10.0)
        recommendation = "HOLD"
        if confidence > 0.7:
            recommendation = "BUY" if market.yes_price < market.no_price else "SELL"
        return {
            "market_id": market.market_id,
            "recommendation": recommendation,
            "confidence": float(confidence),
            "risk": "medium" if confidence > 0.6 else "high",
            "reasoning": "confidence derived from competitiveness and liquidity",
        }

    def compare_markets(self, market_ids: Sequence[str]) -> list[dict[str, Any]]:
        markets = [self.market_details(mid) for mid in market_ids]
        return [
            {
                "market_id": market.market_id,
                "question": market.question,
                "liquidity": market.liquidity,
                "volume_24h": market.volume_24h,
                "close_time": market.close_time,
                "tags": list(market.tags),
            }
            for market in markets
        ]

    def route_mcp_order(self, *, market_id: str, side: str, price: float, size: float) -> Order:
        self._rate_limit("trading")
        self._require_auth()
        market = self.market_details(market_id)
        self._validate_trade(market, size, price)
        order_id = _short_hash(f"{market_id}:{side}:{price}:{size}:{_now_ts()}")
        order = Order(
            order_id=order_id,
            market_id=market_id,
            side=str(side),
            price=float(price),
            size=float(size),
            status="submitted",
            created_at=_now_ts(),
        )
        # Route through canonical router path.
        self.router.submit_order(
            {
                "market_id": market_id,
                "side": side,
                "price": price,
                "size": size,
                "source": "polymarket_mcp",
            }
        )
        self.client.add_order(order)
        return order

    def batch_orders(self, orders: Sequence[Mapping[str, Any]]) -> list[Order]:
        return [
            self.route_mcp_order(
                market_id=str(row["market_id"]),
                side=str(row["side"]),
                price=float(row["price"]),
                size=float(row["size"]),
            )
            for row in orders
        ]

    def open_orders(self) -> list[Order]:
        self._rate_limit("trading")
        return [order for order in self.client.list_orders() if order.status == "submitted"]

    def order_history(self) -> list[Order]:
        self._rate_limit("trading")
        return self.client.list_orders()

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        self._rate_limit("trading")
        removed = self.client.cancel_orders([order_id])
        return {"cancelled": int(removed)}

    def cancel_all(self) -> dict[str, Any]:
        self._rate_limit("trading")
        removed = self.client.cancel_orders([order.order_id for order in self.client.list_orders()])
        return {"cancelled": int(removed)}

    def smart_trade(self, market_id: str, side: str, budget: float) -> Order:
        market = self.market_details(market_id)
        price = market.yes_price if side.lower() == "yes" else market.no_price
        size = float(budget) / max(price, 1e-6)
        return self.route_mcp_order(market_id=market_id, side=side, price=price, size=size)

    def rebalance(self, targets: Sequence[Mapping[str, Any]]) -> list[Order]:
        orders: list[Order] = []
        for target in targets:
            market_id = str(target["market_id"])
            side = str(target.get("side", "yes"))
            size = float(target.get("size", 0.0))
            price = float(target.get("price", 0.0))
            if size <= 0 or price <= 0:
                continue
            orders.append(
                self.route_mcp_order(market_id=market_id, side=side, price=price, size=size)
            )
        return orders

    def portfolio_state(self) -> PortfolioState:
        self._rate_limit("portfolio")
        positions = self.client.list_positions()
        realized = 0.0
        unrealized = 0.0
        for pos in positions:
            pnl = (pos.mark_price - pos.entry_price) * pos.size
            unrealized += pnl
        value = unrealized + realized
        return PortfolioState(
            positions=positions,
            realized_pnl=realized,
            unrealized_pnl=unrealized,
            portfolio_value=value,
            updated_at=_now_ts(),
        )


@dataclass
class WebSocketStatus:
    connected: bool
    last_event_ts: float
    reconnect_attempts: int
    backoff_seconds: float


class WebSocketMonitor:
    def __init__(self, *, max_backoff: float = 60.0) -> None:
        self.connected = False
        self.last_event_ts = 0.0
        self.reconnect_attempts = 0
        self.backoff_seconds = 1.0
        self.max_backoff = max_backoff

    def record_event(self) -> None:
        self.last_event_ts = _now_ts()
        self.connected = True
        self.reconnect_attempts = 0
        self.backoff_seconds = 1.0

    def disconnect(self) -> None:
        self.connected = False

    def schedule_reconnect(self) -> float:
        self.reconnect_attempts += 1
        self.backoff_seconds = min(self.max_backoff, self.backoff_seconds * 2.0)
        return self.backoff_seconds

    def status(self) -> WebSocketStatus:
        return WebSocketStatus(
            connected=self.connected,
            last_event_ts=self.last_event_ts,
            reconnect_attempts=self.reconnect_attempts,
            backoff_seconds=self.backoff_seconds,
        )


@dataclass
class DashboardConfig:
    risk_limits: RiskLimits
    updated_at: float = field(default_factory=_now_ts)


class MCPDashboardAPI:
    def __init__(self, *, server: PolymarketMCPServer, monitor: WebSocketMonitor) -> None:
        self.server = server
        self.monitor = monitor
        self.config = DashboardConfig(risk_limits=server.risk_limits)

    def status(self) -> dict[str, Any]:
        ws = self.monitor.status()
        return {
            "ok": True,
            "websocket_connected": ws.connected,
            "last_event_ts": ws.last_event_ts,
            "reconnect_attempts": ws.reconnect_attempts,
        }

    def test_connection(self) -> dict[str, Any]:
        markets = self.server.client.list_markets()
        return {"ok": True, "market_count": len(markets)}

    def stats(self) -> dict[str, Any]:
        markets = self.server.client.list_markets()
        return {
            "markets": len(markets),
            "timestamp": _now_ts(),
        }

    def update_config(self, *, risk_limits: RiskLimits) -> DashboardConfig:
        self.server.risk_limits = risk_limits
        self.config = DashboardConfig(risk_limits=risk_limits)
        return self.config
