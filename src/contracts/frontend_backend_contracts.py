"""Frontend/backend contracts for graph node events and tool renderer mappings."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

ALLOWED_NODE_STATUSES = {"started", "progress", "completed", "failed"}
REQUIRED_TOOL_RENDERER_TYPES = ("account_summary", "orders_tape", "risk_state")


@dataclass(frozen=True)
class GraphNodeEvent:
    run_id: str
    node_id: str
    node_type: str
    status: str
    timestamp: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_graph_node_event(payload: dict[str, Any]) -> GraphNodeEvent:
    if not isinstance(payload, dict):
        raise ValueError("graph node payload must be an object.")
    required = {"run_id", "node_id", "node_type", "status", "timestamp", "payload"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"graph node payload missing required fields: {sorted(missing)}")
    status = str(payload.get("status", "")).strip().lower()
    if status not in ALLOWED_NODE_STATUSES:
        raise ValueError(f"invalid graph node status `{status}`")
    data = payload.get("payload", {})
    if not isinstance(data, dict):
        raise ValueError("graph node payload field `payload` must be an object.")
    return GraphNodeEvent(
        run_id=str(payload.get("run_id")),
        node_id=str(payload.get("node_id")),
        node_type=str(payload.get("node_type")),
        status=status,
        timestamp=str(payload.get("timestamp")),
        payload=data,
    )


def required_tool_renderer_types() -> tuple[str, ...]:
    return tuple(REQUIRED_TOOL_RENDERER_TYPES)
