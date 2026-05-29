"""Durable append-only store for governed agent proposal decisions."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contracts.execution_flow import OrderIntent
from core.hotpath_runtime import append_lines, event_id
from core.trading_control import (
    AgentProposal,
    AgentProposalApproval,
    AgentProposalQueue,
    AgentProposalQueueResult,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


@dataclass(frozen=True)
class AgentProposalLedgerEvent:
    """Append-only event for proposal lifecycle replay."""

    event_id: str
    timestamp: str
    event_type: str
    proposal_id: str
    agent_id: str
    status: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AgentProposalStore:
    """Recoverable proposal queue backed by an append-only JSONL ledger."""

    def __init__(self, path: str = "data/analytics/agent_proposals.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seen_event_ids: set[str] = set()
        self._queue = AgentProposalQueue()
        self._load_existing()

    @property
    def queue(self) -> AgentProposalQueue:
        return self._queue

    def get(self, proposal_id: str) -> AgentProposal | None:
        return self._queue.get(proposal_id)

    def pending(self) -> tuple[AgentProposal, ...]:
        return self._queue.pending()

    def proposals(self) -> tuple[AgentProposal, ...]:
        return self._queue.proposals()

    def enqueue(self, proposal: AgentProposal, *, now: datetime | None = None) -> AgentProposalQueueResult:
        result = self._queue.enqueue(proposal, now=now)
        event_type = "proposal_queued" if result.accepted else "proposal_rejected"
        self._record_result(event_type=event_type, result=result, extra={"operation": "enqueue"})
        return result

    def approve(
        self,
        proposal_id: str,
        *,
        actor: str,
        actor_role: str,
        reason: str = "",
        now: datetime | None = None,
    ) -> AgentProposalQueueResult:
        result = self._queue.approve(
            proposal_id,
            actor=actor,
            actor_role=actor_role,
            reason=reason,
            now=now,
        )
        event_type = "proposal_approved" if result.accepted else "proposal_decision_rejected"
        self._record_result(event_type=event_type, result=result, extra={"operation": "approve"})
        return result

    def reject(
        self,
        proposal_id: str,
        *,
        actor: str,
        actor_role: str,
        reason: str = "",
        now: datetime | None = None,
    ) -> AgentProposalQueueResult:
        result = self._queue.reject(
            proposal_id,
            actor=actor,
            actor_role=actor_role,
            reason=reason,
            now=now,
        )
        event_type = "proposal_rejected" if result.accepted else "proposal_decision_rejected"
        self._record_result(event_type=event_type, result=result, extra={"operation": "reject"})
        return result

    def materialize_order_intent(self, proposal_id: str, *, mode_state: Any) -> OrderIntent:
        intent = self._queue.materialize_order_intent(proposal_id, mode_state=mode_state)
        proposal = self._queue.get(proposal_id)
        payload = {
            "proposal": proposal.to_dict() if proposal is not None else None,
            "order_intent": intent.to_dict(),
            "operation": "materialize_order_intent",
        }
        self._append_event(
            event_type="proposal_materialized",
            proposal_id=str(proposal_id),
            agent_id=str(intent.metadata.get("agent_proposal", {}).get("agent_id", "")),
            status="materialized",
            payload=payload,
        )
        return intent

    def replay(self, proposal_id: str | None = None) -> list[dict[str, Any]]:
        rows = self._read_events()
        if proposal_id is not None:
            rows = [row for row in rows if str(row.get("proposal_id", "")) == str(proposal_id)]
        rows.sort(key=lambda row: str(row.get("timestamp", "")))
        return rows

    def _record_result(
        self,
        *,
        event_type: str,
        result: AgentProposalQueueResult,
        extra: dict[str, Any] | None = None,
    ) -> None:
        proposal = result.proposal
        payload = result.to_dict()
        payload.update(dict(extra or {}))
        self._append_event(
            event_type=event_type,
            proposal_id=proposal.proposal_id if proposal is not None else "",
            agent_id=proposal.agent_id if proposal is not None else "",
            status=result.status,
            payload=payload,
        )

    def _append_event(
        self,
        *,
        event_type: str,
        proposal_id: str,
        agent_id: str,
        status: str,
        payload: dict[str, Any],
    ) -> bool:
        stable_payload = json.dumps(payload, sort_keys=True, default=_json_default)
        resolved_event_id = event_id(
            "agent_prop",
            (event_type, proposal_id, status, stable_payload),
            hex_len=20,
        )
        if resolved_event_id in self._seen_event_ids:
            return False
        event = AgentProposalLedgerEvent(
            event_id=resolved_event_id,
            timestamp=_utc_now_iso(),
            event_type=str(event_type),
            proposal_id=str(proposal_id),
            agent_id=str(agent_id),
            status=str(status),
            payload=dict(payload),
        )
        append_lines(str(self.path), [json.dumps(event.to_dict(), sort_keys=True, default=_json_default)])
        self._seen_event_ids.add(resolved_event_id)
        return True

    def _load_existing(self) -> None:
        proposals: dict[str, AgentProposal] = {}
        approvals: dict[str, AgentProposalApproval] = {}

        for row in self._read_events():
            event_id_token = str(row.get("event_id", "")).strip()
            if event_id_token:
                self._seen_event_ids.add(event_id_token)
            payload = row.get("payload", {})
            if not isinstance(payload, dict):
                continue
            proposal_payload = payload.get("proposal")
            if isinstance(proposal_payload, dict):
                proposal = AgentProposal.from_dict(proposal_payload)
                proposals[proposal.proposal_id] = proposal
            approval_payload = payload.get("approval")
            if isinstance(approval_payload, dict):
                approval = AgentProposalApproval.from_dict(approval_payload)
                approvals[approval.proposal_id] = approval

        self._queue = AgentProposalQueue(proposals=proposals, approvals=approvals)

    def _read_events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                payload = line.strip()
                if not payload:
                    continue
                try:
                    row = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
        return rows
