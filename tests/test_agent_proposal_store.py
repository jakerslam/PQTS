from __future__ import annotations

from datetime import timedelta

from contracts.execution_flow import OrderIntent
from core.agent_proposal_store import AgentProposalStore
from core.trading_control import AgentProposal, TradingModeState, utc_now


def _proposal(now=None) -> AgentProposal:
    ts = now or utc_now()
    return AgentProposal(
        proposal_id="prop_store_1",
        agent_id="agent_kimi",
        action="create_order_intent",
        strategy_id="pm_micro_alpha",
        rationale="prediction-market microstructure edge with bounded risk",
        supporting_card_ids=("card_pm_micro_1",),
        current_metrics={"edge_bps": 13.0},
        gate_checks={"passed": True, "stage": "paper"},
        risk_impact={"notional_usd": 5000.0, "risk_budget_pct": 2.0},
        approval_required=True,
        expires_at=ts + timedelta(minutes=10),
        order_intent=OrderIntent(
            order_id="oi_prop_store_1",
            strategy_id="pm_micro_alpha",
            symbol="PM-MKT-YES",
            side="buy",
            quantity=100.0,
            order_type="limit",
            requested_price=0.45,
            expected_alpha_bps=13.0,
            source="agent",
            mode="assisted_manual",
            approval_status="proposed",
            market="prediction",
        ),
    )


def test_agent_proposal_store_recovers_approved_queue_and_materializes_intent(tmp_path):
    now = utc_now()
    path = tmp_path / "agent_proposals.jsonl"
    store = AgentProposalStore(path=str(path))

    assert store.enqueue(_proposal(now), now=now).accepted is True
    assert store.approve(
        "prop_store_1",
        actor="ops",
        actor_role="operator",
        reason="evidence reviewed",
        now=now,
    ).accepted is True

    reloaded = AgentProposalStore(path=str(path))
    recovered = reloaded.get("prop_store_1")
    assert recovered is not None
    assert recovered.status == "approved"
    assert reloaded.queue.approval_for("prop_store_1").actor == "ops"

    intent = reloaded.materialize_order_intent(
        "prop_store_1",
        mode_state=TradingModeState(mode="assisted_manual"),
    )

    assert intent.source == "agent"
    assert intent.approval_status == "approved"
    assert intent.metadata["agent_proposal"]["approved_by"] == "ops"

    events = reloaded.replay("prop_store_1")
    assert [event["event_type"] for event in events] == [
        "proposal_queued",
        "proposal_approved",
        "proposal_materialized",
    ]

    final_reload = AgentProposalStore(path=str(path))
    assert final_reload.get("prop_store_1").status == "materialized"


def test_agent_proposal_store_logs_failed_self_approval_without_poisoning_queue(tmp_path):
    now = utc_now()
    path = tmp_path / "agent_proposals.jsonl"
    store = AgentProposalStore(path=str(path))
    store.enqueue(_proposal(now), now=now)

    failed = store.approve(
        "prop_store_1",
        actor="agent_kimi",
        actor_role="operator",
        now=now,
    )

    assert failed.accepted is False
    assert failed.status == "queued"
    assert store.get("prop_store_1").status == "queued"
    assert store.replay("prop_store_1")[-1]["event_type"] == "proposal_decision_rejected"


def test_agent_proposal_store_persists_invalid_rejection_evidence(tmp_path):
    now = utc_now()
    path = tmp_path / "agent_proposals.jsonl"
    invalid = AgentProposal(
        proposal_id="prop_bad",
        agent_id="agent_kimi",
        action="create_order_intent",
        strategy_id="pm_micro_alpha",
        rationale="",
        supporting_card_ids=(),
        current_metrics={},
        gate_checks={},
        risk_impact={},
        approval_required=True,
        expires_at=now - timedelta(seconds=1),
    )
    store = AgentProposalStore(path=str(path))

    rejected = store.enqueue(invalid, now=now)

    assert rejected.accepted is False
    events = store.replay("prop_bad")
    assert len(events) == 1
    assert events[0]["event_type"] == "proposal_rejected"
    assert "proposal_expired" in events[0]["payload"]["reasons"]
