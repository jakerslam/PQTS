"""Contract tests for graph node events and tool renderer mapping completeness."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contracts.frontend_backend_contracts import (
    required_tool_renderer_types,
    validate_graph_node_event,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "apps" / "web" / "lib" / "tools" / "registry.tsx"


def _extract_registry_keys() -> set[str]:
    text = REGISTRY_PATH.read_text(encoding="utf-8")
    pattern = re.compile(r"^\s*([a-z0-9_]+):\s*\{", re.MULTILINE)
    return {match.group(1) for match in pattern.finditer(text)}


def test_tool_renderer_registry_covers_required_types() -> None:
    keys = _extract_registry_keys()
    required = set(required_tool_renderer_types())
    missing = required - keys
    assert missing == set(), f"Missing renderer mappings: {sorted(missing)}"


def test_validate_graph_node_event_accepts_valid_payload() -> None:
    event = validate_graph_node_event(
        {
            "run_id": "run_1",
            "node_id": "node_1",
            "node_type": "retrieval",
            "status": "completed",
            "timestamp": "2026-03-10T00:00:00+00:00",
            "payload": {"duration_ms": 12.0},
        }
    )
    assert event.status == "completed"
    assert event.payload["duration_ms"] == 12.0


def test_validate_graph_node_event_rejects_invalid_status() -> None:
    with pytest.raises(ValueError, match="invalid graph node status"):
        validate_graph_node_event(
            {
                "run_id": "run_2",
                "node_id": "node_2",
                "node_type": "reasoning",
                "status": "unknown",
                "timestamp": "2026-03-10T00:00:00+00:00",
                "payload": {},
            }
        )
