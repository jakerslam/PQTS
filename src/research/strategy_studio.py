"""Hybrid visual+code strategy studio contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from research.anti_leakage_validator import validate_no_lookahead


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class StrategyNode:
    node_id: str
    kind: str
    params: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"node_id": self.node_id, "kind": self.kind, "params": dict(self.params)}


@dataclass(frozen=True)
class StrategyGraph:
    strategy_id: str
    nodes: tuple[StrategyNode, ...]
    edges: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [[left, right] for left, right in self.edges],
        }


def compile_python_strategy(code: str) -> dict[str, Any]:
    token = str(code)
    try:
        compile(token, "<strategy_studio>", "exec")
    except SyntaxError as exc:
        return {"compiled": False, "error": str(exc)}
    return {"compiled": True, "error": ""}


def build_strategy_graph(payload: Mapping[str, Any]) -> StrategyGraph:
    strategy_id = str(payload.get("strategy_id", "untitled")).strip() or "untitled"
    raw_nodes = payload.get("nodes", [])
    raw_edges = payload.get("edges", [])
    nodes: list[StrategyNode] = []
    for row in raw_nodes if isinstance(raw_nodes, list) else []:
        if not isinstance(row, Mapping):
            continue
        node_id = str(row.get("node_id", "")).strip()
        if not node_id:
            continue
        nodes.append(
            StrategyNode(
                node_id=node_id,
                kind=str(row.get("kind", "unknown")).strip() or "unknown",
                params=dict(row.get("params", {})) if isinstance(row.get("params", {}), Mapping) else {},
            )
        )
    edges: list[tuple[str, str]] = []
    for row in raw_edges if isinstance(raw_edges, list) else []:
        if not isinstance(row, Sequence) or len(row) != 2:
            continue
        left = str(row[0]).strip()
        right = str(row[1]).strip()
        if left and right:
            edges.append((left, right))
    return StrategyGraph(strategy_id=strategy_id, nodes=tuple(nodes), edges=tuple(edges))


def simulate_preview(
    *,
    strategy_id: str,
    graph: StrategyGraph,
    code: str,
    sample_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    compile_report = compile_python_strategy(code)
    leakage_report = validate_no_lookahead(sample_rows)
    complexity = len(graph.nodes) + len(graph.edges)
    quality = max(0.0, 1.0 - min(complexity, 100) / 200.0)
    if not compile_report.get("compiled", False):
        quality *= 0.2
    if not leakage_report.get("passed", False):
        quality *= 0.1
    return {
        "strategy_id": str(strategy_id),
        "generated_at": _utc_now(),
        "compile_report": compile_report,
        "leakage_report": leakage_report,
        "preview_quality_score": float(round(quality, 4)),
        "graph": graph.to_dict(),
    }
