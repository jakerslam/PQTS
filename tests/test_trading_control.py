from __future__ import annotations

from datetime import timedelta

from contracts.execution_flow import OrderIntent
from core.trading_control import (
    AgentProposal,
    AgentProposalQueue,
    SteeringCommand,
    TradingModeState,
    evaluate_order_intent,
    evaluate_steering_command,
    mode_capability,
    utc_now,
    validate_agent_proposal,
)


def _intent(**overrides):
    payload = {
        "order_id": "oi_1",
        "strategy_id": "manual_trade",
        "symbol": "BTC-USD",
        "side": "buy",
        "quantity": 0.1,
        "order_type": "limit",
        "requested_price": 50_000.0,
        "expected_alpha_bps": 8.0,
        "source": "human",
        "mode": "manual",
        "approval_status": "proposed",
        "risk_budget_pct": 10.0,
    }
    payload.update(overrides)
    return OrderIntent(**payload)


def test_manual_mode_requires_human_approval_and_blocks_strategy_autopilot() -> None:
    mode = TradingModeState(mode="manual")
    proposed = evaluate_order_intent(
        _intent(),
        mode_state=mode,
        account_equity=100_000.0,
        max_order_notional=20_000.0,
    )
    assert proposed.allowed is False
    assert proposed.requires_approval is True
    assert proposed.reasons == ("operator_approval_required",)

    approved = evaluate_order_intent(
        _intent(approval_status="approved"),
        mode_state=mode,
        account_equity=100_000.0,
        max_order_notional=20_000.0,
    )
    assert approved.allowed is True

    strategy = evaluate_order_intent(
        _intent(source="strategy", approval_status="auto_approved"),
        mode_state=mode,
        account_equity=100_000.0,
        max_order_notional=20_000.0,
    )
    assert strategy.allowed is False
    assert "source_not_allowed_in_manual" in strategy.reasons


def test_paper_autopilot_allows_strategy_but_not_unapproved_agent_execution() -> None:
    mode = TradingModeState(mode="paper_autopilot")
    strategy = evaluate_order_intent(
        _intent(source="strategy", mode="paper_autopilot", approval_status="auto_approved"),
        mode_state=mode,
        account_equity=100_000.0,
        max_order_notional=20_000.0,
    )
    assert strategy.allowed is True

    agent = evaluate_order_intent(
        _intent(source="agent", mode="paper_autopilot"),
        mode_state=mode,
        account_equity=100_000.0,
        max_order_notional=20_000.0,
    )
    assert agent.allowed is False
    assert agent.reasons == ("operator_approval_required",)


def test_live_canary_fails_closed_on_kill_switch_and_sync_drift() -> None:
    mode = TradingModeState(mode="live_canary", live_execution_enabled=True)
    decision = evaluate_order_intent(
        _intent(mode="live_canary", approval_status="approved"),
        mode_state=mode,
        risk_state={"kill_switch_active": True},
        sync_health={"all_clear": False, "fail_closed_trade_block": True},
        account_equity=100_000.0,
    )
    assert decision.allowed is False
    assert decision.hard_block is True
    assert "kill_switch_active" in decision.reasons
    assert "sync_fail_closed" in decision.reasons


def test_kill_only_allows_only_approved_emergency_reduce_sell() -> None:
    mode = TradingModeState(mode="kill_only")
    blocked = evaluate_order_intent(
        _intent(source="human", mode="kill_only", approval_status="approved"),
        mode_state=mode,
    )
    assert blocked.allowed is False
    assert "kill_only_allows_only_emergency_reduce_sell" in blocked.reasons

    allowed = evaluate_order_intent(
        _intent(
            source="emergency",
            mode="kill_only",
            side="sell",
            reduce_only=True,
            approval_status="approved",
        ),
        mode_state=mode,
    )
    assert allowed.allowed is True


def test_steering_commands_require_operator_for_privileged_actions() -> None:
    denied = evaluate_steering_command(
        SteeringCommand(
            action="set_mode", source="agent", requested_by="agent", target_mode="live_autopilot"
        ),
        current_mode="manual",
        actor_role="viewer",
    )
    assert denied.allowed is False
    assert "agent_steering_requires_operator_review" in denied.reasons
    assert "operator_role_required" in denied.reasons

    allowed = evaluate_steering_command(
        SteeringCommand(
            action="set_mode", source="human", requested_by="ops", target_mode="assisted_manual"
        ),
        current_mode="manual",
        actor_role="operator",
    )
    assert allowed.allowed is True
    assert mode_capability("assisted_manual").agent_can_execute is False


def test_agent_proposal_queue_rejects_incomplete_or_expired_proposals() -> None:
    now = utc_now()
    proposal = AgentProposal(
        proposal_id="prop_bad",
        agent_id="agent_1",
        action="create_order_intent",
        strategy_id="pm_micro_alpha",
        rationale="",
        supporting_card_ids=(),
        current_metrics={},
        gate_checks={},
        risk_impact={},
        approval_required=True,
        expires_at=now - timedelta(seconds=1),
        order_intent=_intent(source="agent", mode="assisted_manual"),
    )

    decision = validate_agent_proposal(proposal, now=now)

    assert decision.allowed is False
    assert "rationale_required" in decision.reasons
    assert "supporting_card_ids_required" in decision.reasons
    assert "proposal_expired" in decision.reasons


def test_agent_proposal_queue_requires_operator_approval_before_materializing_intent() -> None:
    now = utc_now()
    queue = AgentProposalQueue()
    proposal = AgentProposal(
        proposal_id="prop_1",
        agent_id="agent_1",
        action="create_order_intent",
        strategy_id="pm_micro_alpha",
        rationale="positive microstructure edge with bounded risk",
        supporting_card_ids=("card_pm_micro_1",),
        current_metrics={"net_edge_bps": 14.2},
        gate_checks={"passed": True, "stage": "paper"},
        risk_impact={"notional_usd": 5000.0, "risk_budget_pct": 2.0},
        approval_required=True,
        expires_at=now + timedelta(minutes=10),
        order_intent=_intent(
            strategy_id="pm_micro_alpha",
            source="agent",
            mode="assisted_manual",
            approval_status="proposed",
            risk_budget_pct=2.0,
        ),
    )

    queued = queue.enqueue(proposal, now=now)
    assert queued.accepted is True

    self_approval = queue.approve(
        proposal.proposal_id,
        actor="agent_1",
        actor_role="operator",
        now=now,
    )
    assert self_approval.accepted is False
    assert "self_approval_not_allowed" in self_approval.reasons

    queue = AgentProposalQueue()
    queue.enqueue(proposal, now=now)
    approved = queue.approve(
        proposal.proposal_id,
        actor="ops_1",
        actor_role="operator",
        reason="reviewed evidence card and risk impact",
        now=now,
    )
    assert approved.accepted is True

    intent = queue.materialize_order_intent(
        proposal.proposal_id,
        mode_state=TradingModeState(mode="assisted_manual"),
    )
    assert intent.source == "agent"
    assert intent.approval_status == "approved"
    assert intent.metadata["agent_proposal"]["proposal_id"] == "prop_1"
