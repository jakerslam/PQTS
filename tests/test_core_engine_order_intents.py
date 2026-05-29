from __future__ import annotations

import asyncio
from datetime import timedelta

from contracts.execution_flow import OrderIntent
from core.engine import TradingEngine
from core.trading_control import AgentProposal, AgentProposalQueue, TradingModeState, utc_now
from execution.risk_aware_router import OrderResult
from risk.kill_switches import RiskDecision


class _FakeRouter:
    def __init__(self) -> None:
        self.submissions = []
        self.risk_limits = type("Limits", (), {"max_order_notional": 20_000.0})()
        self.risk_engine = type(
            "RiskEngine", (), {"get_status": lambda self: {"kill_switch_active": False}}
        )()

    async def fetch_market_snapshot(self):
        return {"last_price": 50_000.0}

    async def submit_order(self, **kwargs):
        self.submissions.append(kwargs)
        return OrderResult(
            success=True,
            decision=RiskDecision.ALLOW,
            risk_state=None,
            order_id="router_ord_1",
            exchange="paper",
            rejected_reason=None,
            audit_log={
                "fill": {"executed_qty": kwargs["order"].quantity, "executed_price": 50_000.0}
            },
        )


def _engine() -> TradingEngine:
    engine = TradingEngine.__new__(TradingEngine)
    engine.mode = "paper_trading"
    engine.trading_mode_state = TradingModeState(mode="paper_autopilot")
    engine.orders = {}
    engine.positions = {}
    engine.market_data = {}
    engine.router = _FakeRouter()
    engine.latest_router_snapshot = {"last_price": 50_000.0}
    engine._portfolio_change_history = [0.0] * 30
    engine._effective_risk_config = lambda: ({"initial_capital": 100_000.0}, object())
    engine._build_portfolio_snapshot = lambda: {"positions": {}, "prices": {}, "leverage": 0.0}
    engine._build_strategy_returns = lambda: {}
    engine._persist_state = lambda: None
    return engine


def test_engine_order_intent_uses_router_submit_order() -> None:
    engine = _engine()
    intent = OrderIntent(
        order_id="oi_router",
        strategy_id="risk_adjusted_momentum",
        symbol="BTC-USD",
        side="buy",
        quantity=0.1,
        order_type="limit",
        requested_price=50_000.0,
        expected_alpha_bps=12.0,
        source="strategy",
        mode="paper_autopilot",
        approval_status="auto_approved",
    )

    result = asyncio.run(engine.submit_order_intent(intent))

    assert result.success is True
    assert len(engine.router.submissions) == 1
    routed = engine.router.submissions[0]["order"]
    assert routed.strategy_id == "risk_adjusted_momentum"
    assert routed.client_order_id == "oi_router"
    assert routed.decision_context["order_intent"]["source"] == "strategy"


def test_engine_rejects_unapproved_manual_order_before_router() -> None:
    engine = _engine()
    engine.trading_mode_state = TradingModeState(mode="manual")
    intent = OrderIntent(
        order_id="oi_manual",
        strategy_id="manual_trade",
        symbol="BTC-USD",
        side="buy",
        quantity=0.1,
        order_type="limit",
        requested_price=50_000.0,
        expected_alpha_bps=0.0,
        source="human",
        mode="manual",
        approval_status="proposed",
    )

    result = asyncio.run(engine.submit_order_intent(intent))

    assert result.success is False
    assert result.rejected_reason == "operator_approval_required"
    assert engine.router.submissions == []


def test_user_mode_approved_human_intent_routes_only_through_router() -> None:
    engine = _engine()
    engine.trading_mode_state = TradingModeState(mode="manual")
    intent = OrderIntent(
        order_id="oi_user",
        strategy_id="manual_trade",
        symbol="BTC-USD",
        side="buy",
        quantity=0.1,
        order_type="limit",
        requested_price=50_000.0,
        expected_alpha_bps=0.0,
        source="human",
        mode="manual",
        approval_status="approved",
    )

    result = asyncio.run(engine.submit_order_intent(intent))

    assert result.success is True
    assert len(engine.router.submissions) == 1
    assert engine.router.submissions[0]["order"].decision_context["order_intent"]["source"] == "human"


def test_agent_steered_mode_requires_approved_proposal_and_uses_router() -> None:
    engine = _engine()
    engine.trading_mode_state = TradingModeState(mode="assisted_manual")
    now = utc_now()
    queue = AgentProposalQueue()
    proposal = AgentProposal(
        proposal_id="prop_agent_route",
        agent_id="agent_kimi",
        action="create_order_intent",
        strategy_id="pm_micro_alpha",
        rationale="operator-reviewed microstructure proposal",
        supporting_card_ids=("card_1",),
        current_metrics={"edge_bps": 11.0},
        gate_checks={"passed": True},
        risk_impact={"notional_usd": 5000.0},
        approval_required=True,
        expires_at=now + timedelta(minutes=5),
        order_intent=OrderIntent(
            order_id="oi_agent",
            strategy_id="pm_micro_alpha",
            symbol="BTC-USD",
            side="buy",
            quantity=0.1,
            order_type="limit",
            requested_price=50_000.0,
            expected_alpha_bps=11.0,
            source="agent",
            mode="assisted_manual",
            approval_status="proposed",
        ),
    )
    assert queue.enqueue(proposal, now=now).accepted is True

    blocked = asyncio.run(engine.submit_order_intent(proposal.order_intent))
    assert blocked.success is False
    assert engine.router.submissions == []

    assert queue.approve(
        proposal.proposal_id,
        actor="ops",
        actor_role="operator",
        now=now,
    ).accepted
    approved_intent = queue.materialize_order_intent(
        proposal.proposal_id,
        mode_state=engine.trading_mode_state,
    )
    routed = asyncio.run(engine.submit_order_intent(approved_intent))

    assert routed.success is True
    assert len(engine.router.submissions) == 1
    decision_context = engine.router.submissions[0]["order"].decision_context
    assert decision_context["order_intent"]["source"] == "agent"
    assert decision_context["order_intent"]["metadata"]["agent_proposal"]["proposal_id"]


def test_auto_mode_strategy_intent_routes_only_through_router() -> None:
    engine = _engine()
    engine.trading_mode_state = TradingModeState(mode="paper_autopilot")
    intent = OrderIntent(
        order_id="oi_auto",
        strategy_id="risk_adjusted_momentum",
        symbol="BTC-USD",
        side="buy",
        quantity=0.1,
        order_type="limit",
        requested_price=50_000.0,
        expected_alpha_bps=9.0,
        source="strategy",
        mode="paper_autopilot",
        approval_status="auto_approved",
    )

    result = asyncio.run(engine.submit_order_intent(intent))

    assert result.success is True
    assert len(engine.router.submissions) == 1
    assert engine.router.submissions[0]["order"].decision_context["order_intent"]["source"] == "strategy"
