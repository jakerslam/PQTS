"""Trading-mode and order-intent guardrails for manual/agent/autopilot flows."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Mapping

from contracts.execution_flow import OrderIntent

TRADING_MODES = {
    "manual",
    "assisted_manual",
    "paper_autopilot",
    "live_canary",
    "live_autopilot",
    "kill_only",
}

ORDER_SOURCES = {"human", "agent", "strategy", "emergency"}
APPROVAL_STATUSES = {"proposed", "simulated", "approved", "auto_approved", "rejected", "submitted"}
STEERING_ACTIONS = {
    "pause_strategy",
    "resume_strategy",
    "exclude_symbol",
    "include_symbol",
    "set_risk_budget",
    "force_paper_only",
    "set_mode",
    "kill_only",
    "flatten_symbol",
    "flatten_all",
}
AGENT_PROPOSAL_ACTIONS = {
    "create_order_intent",
    "hedge_position",
    "adjust_risk_budget",
    "pause_strategy",
    "resume_strategy",
    "promote_to_paper",
    "promote_to_live_canary",
    "promote_to_live",
    "hold",
    "demote",
    "kill",
}
CAPITAL_AFFECTING_AGENT_PROPOSAL_ACTIONS = {
    "create_order_intent",
    "hedge_position",
    "adjust_risk_budget",
    "promote_to_live_canary",
    "promote_to_live",
}
LOW_RISK_AGENT_PROPOSAL_ACTIONS = {"hold", "pause_strategy", "resume_strategy", "demote", "kill"}
ORDER_INTENT_AGENT_PROPOSAL_ACTIONS = {"create_order_intent", "hedge_position"}
AGENT_PROPOSAL_STATUSES = {"queued", "approved", "rejected", "expired", "materialized"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_utc_datetime(value: Any, *, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    else:
        raise ValueError(f"{field_name} is required")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class TradingModeState:
    """Current governed trading mode."""

    mode: str = "manual"
    live_execution_enabled: bool = False
    updated_by: str = "system"
    reason: str = ""
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["updated_at"] = self.updated_at.isoformat()
        return out


@dataclass(frozen=True)
class ModeCapability:
    """Capabilities exposed by a trading mode."""

    mode: str
    allowed_sources: tuple[str, ...]
    live_capable: bool
    strategy_autopilot_allowed: bool
    agent_can_execute: bool
    requires_approval_for_sources: tuple[str, ...]
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "allowed_sources": list(self.allowed_sources),
            "live_capable": self.live_capable,
            "strategy_autopilot_allowed": self.strategy_autopilot_allowed,
            "agent_can_execute": self.agent_can_execute,
            "requires_approval_for_sources": list(self.requires_approval_for_sources),
            "description": self.description,
        }


@dataclass(frozen=True)
class ControlGateDecision:
    """Fail-closed gate result for one control-plane action."""

    allowed: bool
    requires_approval: bool
    hard_block: bool
    reasons: tuple[str, ...] = ()
    checks: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "requires_approval": self.requires_approval,
            "hard_block": self.hard_block,
            "reasons": list(self.reasons),
            "checks": dict(self.checks),
        }


@dataclass(frozen=True)
class SteeringCommand:
    """Human or agent steering request."""

    action: str
    source: str
    requested_by: str
    reason: str = ""
    strategy_id: str = ""
    symbol: str = ""
    risk_budget_pct: float = 0.0
    target_mode: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentProposal:
    """Structured agent recommendation before any order intent can be routed."""

    proposal_id: str
    agent_id: str
    action: str
    strategy_id: str
    rationale: str
    supporting_card_ids: tuple[str, ...]
    current_metrics: Mapping[str, Any]
    gate_checks: Mapping[str, Any]
    risk_impact: Mapping[str, Any]
    approval_required: bool
    expires_at: datetime
    counterevidence_card_ids: tuple[str, ...] = ()
    recommended_mode: str = ""
    order_intent: OrderIntent | None = None
    status: str = "queued"
    created_at: datetime = field(default_factory=utc_now)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AgentProposal":
        order_payload = payload.get("order_intent") or payload.get("order_intent_payload")
        order_intent = (
            OrderIntent.from_dict(dict(order_payload)) if isinstance(order_payload, Mapping) else None
        )
        return cls(
            proposal_id=str(payload.get("proposal_id", "")).strip(),
            agent_id=str(payload.get("agent_id", "")).strip(),
            action=str(payload.get("action", "")).strip().lower(),
            strategy_id=str(payload.get("strategy_id", "")).strip(),
            rationale=str(payload.get("rationale", "")).strip(),
            supporting_card_ids=tuple(
                str(item).strip()
                for item in payload.get("supporting_card_ids", ())
                if str(item).strip()
            ),
            counterevidence_card_ids=tuple(
                str(item).strip()
                for item in payload.get("counterevidence_card_ids", ())
                if str(item).strip()
            ),
            current_metrics=dict(payload.get("current_metrics", {}) or {}),
            gate_checks=dict(payload.get("gate_checks", {}) or {}),
            risk_impact=dict(payload.get("risk_impact", {}) or {}),
            approval_required=bool(payload.get("approval_required", True)),
            expires_at=_coerce_utc_datetime(payload.get("expires_at"), field_name="expires_at"),
            recommended_mode=str(payload.get("recommended_mode", "")).strip().lower(),
            order_intent=order_intent,
            status=str(payload.get("status", "queued")).strip().lower() or "queued",
            created_at=_coerce_utc_datetime(
                payload.get("created_at", utc_now()), field_name="created_at"
            ),
            metadata=dict(payload.get("metadata", {}) or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        out = {
            "proposal_id": self.proposal_id,
            "agent_id": self.agent_id,
            "action": self.action,
            "strategy_id": self.strategy_id,
            "rationale": self.rationale,
            "supporting_card_ids": list(self.supporting_card_ids),
            "counterevidence_card_ids": list(self.counterevidence_card_ids),
            "current_metrics": dict(self.current_metrics),
            "gate_checks": dict(self.gate_checks),
            "risk_impact": dict(self.risk_impact),
            "approval_required": self.approval_required,
            "expires_at": self.expires_at.isoformat(),
            "recommended_mode": self.recommended_mode,
            "order_intent": self.order_intent.to_dict() if self.order_intent else None,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "metadata": dict(self.metadata),
        }
        return out


@dataclass(frozen=True)
class AgentProposalApproval:
    """Operator approval/rejection receipt for one agent proposal."""

    approval_id: str
    proposal_id: str
    decision: str
    actor: str
    actor_role: str
    reason: str = ""
    decided_at: datetime = field(default_factory=utc_now)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AgentProposalApproval":
        return cls(
            approval_id=str(payload.get("approval_id", "")).strip(),
            proposal_id=str(payload.get("proposal_id", "")).strip(),
            decision=str(payload.get("decision", "")).strip().lower(),
            actor=str(payload.get("actor", "")).strip(),
            actor_role=str(payload.get("actor_role", "")).strip().lower(),
            reason=str(payload.get("reason", "")).strip(),
            decided_at=_coerce_utc_datetime(
                payload.get("decided_at", utc_now()), field_name="decided_at"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["decided_at"] = self.decided_at.isoformat()
        return out


@dataclass(frozen=True)
class AgentProposalQueueResult:
    """Queue operation result with explicit reason codes."""

    accepted: bool
    status: str
    reasons: tuple[str, ...] = ()
    proposal: AgentProposal | None = None
    approval: AgentProposalApproval | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "reasons": list(self.reasons),
            "proposal": self.proposal.to_dict() if self.proposal else None,
            "approval": self.approval.to_dict() if self.approval else None,
        }


def normalize_trading_mode(value: Any) -> str:
    token = str(value or "").strip().lower()
    if token in {"paper", "paper_trading"}:
        token = "paper_autopilot"
    elif token in {"live", "live_trading"}:
        token = "live_canary"
    if token not in TRADING_MODES:
        raise ValueError(f"invalid trading mode: {value}")
    return token


def normalize_source(value: Any) -> str:
    token = str(value or "strategy").strip().lower()
    if token not in ORDER_SOURCES:
        raise ValueError(f"invalid order source: {value}")
    return token


def normalize_approval_status(value: Any) -> str:
    token = str(value or "proposed").strip().lower()
    if token not in APPROVAL_STATUSES:
        raise ValueError(f"invalid approval status: {value}")
    return token


def normalize_agent_proposal_action(value: Any) -> str:
    token = str(value or "").strip().lower()
    if token not in AGENT_PROPOSAL_ACTIONS:
        raise ValueError(f"invalid agent proposal action: {value}")
    return token


def normalize_agent_proposal_status(value: Any) -> str:
    token = str(value or "queued").strip().lower()
    if token not in AGENT_PROPOSAL_STATUSES:
        raise ValueError(f"invalid agent proposal status: {value}")
    return token


def default_mode_for_engine_mode(engine_mode: str) -> str:
    token = str(engine_mode or "").strip().lower()
    if token in {"live", "live_trading"}:
        return "live_canary"
    if token in {"paper", "paper_trading", "backtest"}:
        return "paper_autopilot"
    return "manual"


def validate_agent_proposal(
    proposal: AgentProposal,
    *,
    now: datetime | None = None,
) -> ControlGateDecision:
    """Validate a queued agent proposal before operator review."""

    reasons: list[str] = []
    checks: dict[str, Any] = {}
    current_time = (now or utc_now()).astimezone(timezone.utc)
    action = str(proposal.action).strip().lower()
    status = str(proposal.status).strip().lower()

    checks["proposal_id"] = proposal.proposal_id
    checks["agent_id"] = proposal.agent_id
    checks["action"] = action
    checks["strategy_id"] = proposal.strategy_id
    checks["expires_at"] = proposal.expires_at.isoformat()
    checks["approval_required"] = bool(proposal.approval_required)
    checks["status"] = status

    if not proposal.proposal_id:
        reasons.append("proposal_id_required")
    if not proposal.agent_id:
        reasons.append("agent_id_required")
    if not proposal.strategy_id:
        reasons.append("strategy_id_required")
    if not proposal.rationale:
        reasons.append("rationale_required")
    if action not in AGENT_PROPOSAL_ACTIONS:
        reasons.append("unsupported_agent_proposal_action")
    if status not in AGENT_PROPOSAL_STATUSES:
        reasons.append("invalid_agent_proposal_status")
    if not proposal.supporting_card_ids:
        reasons.append("supporting_card_ids_required")
    if not dict(proposal.current_metrics):
        reasons.append("current_metrics_required")
    if not dict(proposal.gate_checks):
        reasons.append("gate_checks_required")
    if not dict(proposal.risk_impact):
        reasons.append("risk_impact_required")
    if proposal.expires_at <= current_time:
        reasons.append("proposal_expired")

    capital_affecting = action in CAPITAL_AFFECTING_AGENT_PROPOSAL_ACTIONS
    checks["capital_affecting"] = capital_affecting
    if capital_affecting and not proposal.approval_required:
        reasons.append("capital_affecting_proposal_requires_approval")
    if not proposal.approval_required and action not in LOW_RISK_AGENT_PROPOSAL_ACTIONS:
        reasons.append("preauthorization_not_allowed_for_action")

    if action in ORDER_INTENT_AGENT_PROPOSAL_ACTIONS:
        if proposal.order_intent is None:
            reasons.append("order_intent_required_for_action")
        else:
            intent = proposal.order_intent
            intent_source = normalize_source(intent.source)
            intent_approval = normalize_approval_status(intent.approval_status)
            checks["order_intent_source"] = intent_source
            checks["order_intent_approval_status"] = intent_approval
            if intent_source != "agent":
                reasons.append("order_intent_source_must_be_agent")
            if intent_approval == "auto_approved":
                reasons.append("agent_order_intent_cannot_be_auto_approved")
            if str(intent.strategy_id).strip() != proposal.strategy_id:
                reasons.append("order_intent_strategy_id_mismatch")

    return ControlGateDecision(
        allowed=len(reasons) == 0,
        requires_approval=bool(proposal.approval_required),
        hard_block=any(
            reason
            in {
                "proposal_expired",
                "agent_order_intent_cannot_be_auto_approved",
                "capital_affecting_proposal_requires_approval",
            }
            for reason in reasons
        ),
        reasons=tuple(reasons),
        checks=checks,
    )


class AgentProposalQueue:
    """In-memory proposal queue enforcing operator approval before materialization.

    The queue never places orders. Approved trade proposals can only become an
    `OrderIntent`, which still has to pass `TradingEngine.submit_order_intent()`.
    """

    def __init__(
        self,
        proposals: Mapping[str, AgentProposal] | None = None,
        approvals: Mapping[str, AgentProposalApproval] | None = None,
    ) -> None:
        self._proposals: dict[str, AgentProposal] = dict(proposals or {})
        self._approvals: dict[str, AgentProposalApproval] = dict(approvals or {})

    def enqueue(
        self,
        proposal: AgentProposal,
        *,
        now: datetime | None = None,
    ) -> AgentProposalQueueResult:
        gate = validate_agent_proposal(proposal, now=now)
        if not gate.allowed:
            return AgentProposalQueueResult(
                accepted=False,
                status="rejected",
                reasons=gate.reasons,
                proposal=replace(proposal, status="rejected"),
            )
        queued = replace(proposal, status="queued")
        self._proposals[queued.proposal_id] = queued
        return AgentProposalQueueResult(accepted=True, status="queued", proposal=queued)

    def get(self, proposal_id: str) -> AgentProposal | None:
        return self._proposals.get(str(proposal_id).strip())

    def pending(self) -> tuple[AgentProposal, ...]:
        return tuple(
            proposal for proposal in self._proposals.values() if proposal.status == "queued"
        )

    def proposals(self) -> tuple[AgentProposal, ...]:
        return tuple(
            sorted(
                self._proposals.values(),
                key=lambda proposal: (proposal.created_at, proposal.proposal_id),
                reverse=True,
            )
        )

    def approval_for(self, proposal_id: str) -> AgentProposalApproval | None:
        return self._approvals.get(str(proposal_id).strip())

    def approve(
        self,
        proposal_id: str,
        *,
        actor: str,
        actor_role: str,
        reason: str = "",
        now: datetime | None = None,
    ) -> AgentProposalQueueResult:
        return self._decide(
            proposal_id,
            decision="approved",
            actor=actor,
            actor_role=actor_role,
            reason=reason,
            now=now,
        )

    def reject(
        self,
        proposal_id: str,
        *,
        actor: str,
        actor_role: str,
        reason: str = "",
        now: datetime | None = None,
    ) -> AgentProposalQueueResult:
        return self._decide(
            proposal_id,
            decision="rejected",
            actor=actor,
            actor_role=actor_role,
            reason=reason,
            now=now,
        )

    def materialize_order_intent(
        self,
        proposal_id: str,
        *,
        mode_state: TradingModeState,
    ) -> OrderIntent:
        proposal = self._proposals.get(str(proposal_id).strip())
        if proposal is None:
            raise ValueError("agent proposal not found")
        if proposal.status != "approved":
            raise ValueError("agent proposal must be approved before order intent materialization")
        if proposal.action not in ORDER_INTENT_AGENT_PROPOSAL_ACTIONS:
            raise ValueError("agent proposal action does not materialize an order intent")
        if proposal.order_intent is None:
            raise ValueError("agent proposal has no order intent")
        approval = self._approvals.get(proposal.proposal_id)
        payload = proposal.order_intent.to_dict()
        metadata = dict(payload.get("metadata", {}) or {})
        metadata["agent_proposal"] = {
            "proposal_id": proposal.proposal_id,
            "agent_id": proposal.agent_id,
            "approved_by": approval.actor if approval is not None else "",
            "approved_at": approval.decided_at.isoformat() if approval is not None else "",
            "supporting_card_ids": list(proposal.supporting_card_ids),
        }
        payload.update(
            {
                "strategy_id": proposal.strategy_id,
                "source": "agent",
                "mode": normalize_trading_mode(mode_state.mode),
                "approval_status": "approved",
                "metadata": metadata,
            }
        )
        materialized = OrderIntent.from_dict(payload)
        self._proposals[proposal.proposal_id] = replace(proposal, status="materialized")
        return materialized

    def _decide(
        self,
        proposal_id: str,
        *,
        decision: str,
        actor: str,
        actor_role: str,
        reason: str,
        now: datetime | None,
    ) -> AgentProposalQueueResult:
        key = str(proposal_id).strip()
        proposal = self._proposals.get(key)
        if proposal is None:
            return AgentProposalQueueResult(
                accepted=False,
                status="rejected",
                reasons=("proposal_not_found",),
            )

        reasons: list[str] = []
        role = str(actor_role or "").strip().lower()
        actor_id = str(actor or "").strip()
        if role not in {"operator", "admin"}:
            reasons.append("operator_role_required")
        if actor_id and actor_id == proposal.agent_id:
            reasons.append("self_approval_not_allowed")
        if proposal.status != "queued":
            reasons.append("proposal_not_queued")

        current_time = (now or utc_now()).astimezone(timezone.utc)
        if proposal.expires_at <= current_time:
            reasons.append("proposal_expired")
        if proposal.action in CAPITAL_AFFECTING_AGENT_PROPOSAL_ACTIONS:
            if proposal.gate_checks.get("passed") is False:
                reasons.append("gate_checks_not_passed")

        if decision == "approved":
            validation = validate_agent_proposal(proposal, now=now)
            if not validation.allowed:
                reasons.extend(validation.reasons)

        if reasons:
            terminal_reasons = {
                "proposal_expired",
                "proposal_not_queued",
                "gate_checks_not_passed",
                "proposal_id_required",
                "agent_id_required",
                "strategy_id_required",
                "rationale_required",
                "supporting_card_ids_required",
                "current_metrics_required",
                "gate_checks_required",
                "risk_impact_required",
                "capital_affecting_proposal_requires_approval",
                "agent_order_intent_cannot_be_auto_approved",
                "order_intent_source_must_be_agent",
            }
            if "proposal_expired" in reasons:
                status = "expired"
            elif terminal_reasons.intersection(reasons):
                status = "rejected"
            else:
                status = proposal.status
            updated = replace(proposal, status=status)
            self._proposals[key] = updated
            return AgentProposalQueueResult(
                accepted=False,
                status=status,
                reasons=tuple(sorted(set(reasons))),
                proposal=updated,
            )

        normalized_decision = "approved" if decision == "approved" else "rejected"
        approval = AgentProposalApproval(
            approval_id=f"appr_{key}",
            proposal_id=key,
            decision=normalized_decision,
            actor=actor_id,
            actor_role=role,
            reason=str(reason or "").strip(),
            decided_at=current_time,
        )
        updated = replace(proposal, status=normalized_decision)
        self._proposals[key] = updated
        self._approvals[key] = approval
        return AgentProposalQueueResult(
            accepted=True,
            status=normalized_decision,
            proposal=updated,
            approval=approval,
        )


def mode_capability(mode: str) -> ModeCapability:
    normalized = normalize_trading_mode(mode)
    specs = {
        "manual": ModeCapability(
            mode="manual",
            allowed_sources=("human", "emergency"),
            live_capable=False,
            strategy_autopilot_allowed=False,
            agent_can_execute=False,
            requires_approval_for_sources=("human", "emergency"),
            description="Human-directed order intents only; strategies and agents can observe/propose elsewhere.",
        ),
        "assisted_manual": ModeCapability(
            mode="assisted_manual",
            allowed_sources=("human", "agent", "emergency"),
            live_capable=False,
            strategy_autopilot_allowed=False,
            agent_can_execute=False,
            requires_approval_for_sources=("human", "agent", "emergency"),
            description="Human-led trading with agent proposals and explanations; approval remains human.",
        ),
        "paper_autopilot": ModeCapability(
            mode="paper_autopilot",
            allowed_sources=("human", "agent", "strategy", "emergency"),
            live_capable=False,
            strategy_autopilot_allowed=True,
            agent_can_execute=False,
            requires_approval_for_sources=("human", "agent", "emergency"),
            description="Autopilot may submit paper orders; human and agent intents still require approval.",
        ),
        "live_canary": ModeCapability(
            mode="live_canary",
            allowed_sources=("human", "agent", "strategy", "emergency"),
            live_capable=True,
            strategy_autopilot_allowed=True,
            agent_can_execute=False,
            requires_approval_for_sources=("human", "agent", "strategy", "emergency"),
            description="Tiny live allocation only after approval, paper/canary gates, sync health, and kill checks.",
        ),
        "live_autopilot": ModeCapability(
            mode="live_autopilot",
            allowed_sources=("human", "agent", "strategy", "emergency"),
            live_capable=True,
            strategy_autopilot_allowed=True,
            agent_can_execute=False,
            requires_approval_for_sources=("human", "agent", "strategy", "emergency"),
            description="Live autopilot is available only for approved intents behind hard gates.",
        ),
        "kill_only": ModeCapability(
            mode="kill_only",
            allowed_sources=("emergency",),
            live_capable=False,
            strategy_autopilot_allowed=False,
            agent_can_execute=False,
            requires_approval_for_sources=("emergency",),
            description="No new risk; only approved emergency reduce-only/flatten actions are admissible.",
        ),
    }
    return specs[normalized]


def trading_mode_state_from_config(
    config: Mapping[str, Any],
    *,
    updated_by: str = "system",
) -> TradingModeState:
    runtime = config.get("runtime", {}) if isinstance(config, Mapping) else {}
    runtime_cfg = runtime if isinstance(runtime, Mapping) else {}
    control = runtime_cfg.get("trading_control", {})
    control_cfg = control if isinstance(control, Mapping) else {}
    default_mode = default_mode_for_engine_mode(str(config.get("mode", "")))
    mode = normalize_trading_mode(control_cfg.get("mode", default_mode))
    live_enabled = bool(control_cfg.get("live_execution_enabled", mode.startswith("live")))
    if not mode.startswith("live"):
        live_enabled = False
    return TradingModeState(
        mode=mode,
        live_execution_enabled=live_enabled,
        updated_by=str(control_cfg.get("updated_by", updated_by)),
        reason=str(control_cfg.get("reason", "engine_startup_default")),
    )


def order_intent_notional(intent: OrderIntent) -> float:
    explicit = float(getattr(intent, "notional_usd", 0.0) or 0.0)
    if explicit > 0.0:
        return explicit
    return abs(float(intent.quantity) * float(intent.requested_price or 0.0))


def _risk_is_clear(risk_state: Mapping[str, Any] | None) -> tuple[bool, str]:
    if not risk_state:
        return True, "risk_state_unavailable_router_will_enforce"
    if bool(risk_state.get("kill_switch_active", False)):
        return False, "kill_switch_active"
    level = str(risk_state.get("risk_level", "")).strip().lower()
    if level == "critical":
        return False, "risk_level_critical"
    return True, "ok"


def _sync_is_clear(sync_health: Mapping[str, Any] | None) -> tuple[bool, str]:
    if not sync_health:
        return True, "sync_health_unavailable_router_will_enforce"
    if bool(sync_health.get("fail_closed_trade_block", False)):
        return False, "sync_fail_closed"
    if bool(sync_health.get("all_clear", True)) is False:
        return False, "sync_not_clear"
    return True, "ok"


def evaluate_order_intent(
    intent: OrderIntent,
    *,
    mode_state: TradingModeState,
    risk_state: Mapping[str, Any] | None = None,
    sync_health: Mapping[str, Any] | None = None,
    account_equity: float | None = None,
    max_order_notional: float | None = None,
) -> ControlGateDecision:
    """Evaluate one order intent before it can be handed to the router."""

    reasons: list[str] = []
    checks: dict[str, Any] = {}
    mode = normalize_trading_mode(mode_state.mode)
    source = normalize_source(intent.source)
    approval = normalize_approval_status(intent.approval_status)
    capability = mode_capability(mode)
    intent_mode = normalize_trading_mode(intent.mode or mode)
    notional = order_intent_notional(intent)
    side = str(intent.side).strip().lower()
    reduce_only = bool(intent.reduce_only or intent.metadata.get("reduce_only", False))

    checks["mode"] = mode
    checks["intent_mode"] = intent_mode
    checks["source"] = source
    checks["approval_status"] = approval
    checks["notional_usd"] = notional
    checks["reduce_only"] = reduce_only

    if intent_mode != mode:
        reasons.append("intent_mode_mismatch")
    if source not in capability.allowed_sources:
        reasons.append(f"source_not_allowed_in_{mode}")
    if float(intent.quantity) <= 0.0:
        reasons.append("quantity_must_be_positive")
    if side not in {"buy", "sell"}:
        reasons.append("side_must_be_buy_or_sell")

    if mode == "kill_only":
        if source != "emergency" or not reduce_only or side != "sell":
            reasons.append("kill_only_allows_only_emergency_reduce_sell")

    risk_clear, risk_reason = _risk_is_clear(risk_state)
    sync_clear, sync_reason = _sync_is_clear(sync_health)
    checks["risk_clear"] = risk_clear
    checks["risk_reason"] = risk_reason
    checks["sync_clear"] = sync_clear
    checks["sync_reason"] = sync_reason

    if not risk_clear:
        reasons.append(risk_reason)
    if mode.startswith("live"):
        if not mode_state.live_execution_enabled:
            reasons.append("live_execution_not_enabled")
        if not sync_clear:
            reasons.append(sync_reason)

    if max_order_notional is not None and max_order_notional > 0.0:
        checks["max_order_notional"] = float(max_order_notional)
        if notional > float(max_order_notional):
            reasons.append("order_notional_exceeds_limit")

    risk_budget_pct = float(intent.risk_budget_pct or 0.0)
    if account_equity is not None and account_equity > 0.0 and risk_budget_pct > 0.0:
        budget_notional = float(account_equity) * (risk_budget_pct / 100.0)
        checks["risk_budget_notional"] = budget_notional
        if notional > budget_notional:
            reasons.append("order_notional_exceeds_intent_risk_budget")

    requires_approval = source in capability.requires_approval_for_sources
    if mode.startswith("live"):
        requires_approval = True
    checks["requires_approval"] = requires_approval
    checks["agent_can_execute"] = capability.agent_can_execute

    if source == "agent" and approval == "auto_approved":
        checks["agent_execution_blocked"] = True
        reasons.append("agent_may_not_self_execute")

    if requires_approval and approval not in {"approved", "auto_approved"}:
        reasons.append("operator_approval_required")

    hard_block = any(
        reason
        in {
            "kill_switch_active",
            "risk_level_critical",
            "sync_fail_closed",
            "sync_not_clear",
            "live_execution_not_enabled",
            "source_not_allowed_in_kill_only",
        }
        for reason in reasons
    )
    return ControlGateDecision(
        allowed=len(reasons) == 0,
        requires_approval=requires_approval,
        hard_block=hard_block,
        reasons=tuple(reasons),
        checks=checks,
    )


def evaluate_steering_command(
    command: SteeringCommand,
    *,
    current_mode: str,
    actor_role: str,
) -> ControlGateDecision:
    """Evaluate a human or agent steering command without changing state."""

    action = str(command.action).strip().lower()
    source = normalize_source(command.source)
    role = str(actor_role or "viewer").strip().lower()
    reasons: list[str] = []
    checks = {
        "action": action,
        "source": source,
        "actor_role": role,
        "current_mode": normalize_trading_mode(current_mode),
    }

    if action not in STEERING_ACTIONS:
        reasons.append("unsupported_steering_action")
    if source == "agent" and action in {"set_mode", "kill_only", "flatten_symbol", "flatten_all"}:
        reasons.append("agent_steering_requires_operator_review")
    if action in {"set_mode", "kill_only", "flatten_symbol", "flatten_all"} and role not in {
        "operator",
        "admin",
    }:
        reasons.append("operator_role_required")
    if action == "set_mode":
        try:
            target = normalize_trading_mode(command.target_mode)
            checks["target_mode"] = target
        except ValueError:
            reasons.append("invalid_target_mode")
    if action == "set_risk_budget" and float(command.risk_budget_pct or 0.0) <= 0.0:
        reasons.append("risk_budget_pct_required")

    requires_approval = source == "agent" or role not in {"operator", "admin"}
    if requires_approval and action in {"set_mode", "kill_only", "flatten_symbol", "flatten_all"}:
        reasons.append("operator_approval_required")

    return ControlGateDecision(
        allowed=len(reasons) == 0,
        requires_approval=requires_approval,
        hard_block=False,
        reasons=tuple(reasons),
        checks=checks,
    )
