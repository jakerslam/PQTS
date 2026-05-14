from __future__ import annotations

import time

import pytest

from integrations.polymarket_mcp import (
    MCPDashboardAPI,
    MCPError,
    Market,
    PolymarketClient,
    PolymarketMCPServer,
    RiskLimits,
    WebSocketMonitor,
)


class DummyRouter:
    def __init__(self) -> None:
        self.submitted: list[dict] = []

    def submit_order(self, payload: dict) -> None:
        self.submitted.append(payload)


def _server() -> PolymarketMCPServer:
    markets = [
        Market(
            market_id="1",
            question="BTC up today?",
            tags=("crypto", "featured"),
            liquidity=200,
            yes_price=0.6,
            no_price=0.4,
            volume_24h=1200,
            volume_7d=5000,
            volume_30d=12000,
            price_change_24h=0.05,
            close_time=time.time() + 3600,
        ),
        Market(
            market_id="2",
            question="Team A wins?",
            tags=("sports",),
            liquidity=80,
            yes_price=0.52,
            no_price=0.48,
            volume_24h=300,
            volume_7d=900,
            volume_30d=2000,
        ),
    ]
    client = PolymarketClient(markets=markets)
    router = DummyRouter()
    return PolymarketMCPServer(client=client, router=router, risk_limits=RiskLimits(max_spread=0.3))


def test_tool_inventory_and_discovery() -> None:
    server = _server()
    tools = server.list_tools()
    assert any(tool.name == "market_search" for tool in tools)
    assert server.search_markets("BTC")[0].market_id == "1"
    assert server.crypto()[0].market_id == "1"
    assert server.sports()[0].market_id == "2"
    assert server.featured()[0].market_id == "1"


def test_market_analysis_and_opportunity() -> None:
    server = _server()
    details = server.market_details("1")
    spread = server.market_spread("1")
    assert details.market_id == "1"
    assert spread["spread"] > 0
    analysis = server.opportunity_analysis("1")
    assert analysis["recommendation"] in {"BUY", "SELL", "HOLD", "AVOID"}


def test_trading_requires_auth_and_limits() -> None:
    server = _server()
    with pytest.raises(MCPError):
        server.route_mcp_order(market_id="1", side="yes", price=0.6, size=1)
    server.auth = server.auth.__class__(mode="l2", wallet_address="0xabc")
    order = server.route_mcp_order(market_id="1", side="yes", price=0.6, size=1)
    assert order.market_id == "1"
    assert len(server.router.submitted) == 1


def test_rate_limit_and_validation() -> None:
    server = _server()
    server.rate_limits["trading"].capacity = 0
    server.auth = server.auth.__class__(mode="l2", wallet_address="0xabc")
    with pytest.raises(MCPError):
        server.route_mcp_order(market_id="1", side="yes", price=0.6, size=1)


def test_dashboard_and_websocket_status() -> None:
    server = _server()
    monitor = WebSocketMonitor()
    api = MCPDashboardAPI(server=server, monitor=monitor)
    status = api.status()
    assert status["ok"] is True
    monitor.record_event()
    status = api.status()
    assert status["websocket_connected"] is True
    cfg = api.update_config(risk_limits=RiskLimits(max_order_size=10))
    assert cfg.risk_limits.max_order_size == 10
