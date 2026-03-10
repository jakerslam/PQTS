from __future__ import annotations

import json
from pathlib import Path

from tools import check_scope_governance


def test_check_scope_governance_tool_passes_primary_wedge(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "check_scope_governance.py",
            "--requested-markets",
            "crypto",
        ],
    )
    assert check_scope_governance.main() == 0


def test_check_scope_governance_tool_blocks_unready_expansion(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "cfg.yaml"
    config_path.write_text("runtime: {}\n", encoding="utf-8")
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "primary_wedge_market": "crypto",
                "max_additional_markets_per_phase": 1,
                "readiness_gates": {
                    "min_execution_quality": 0.8,
                    "min_reconciliation_accuracy": 0.99,
                    "max_open_p1_incidents": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "check_scope_governance.py",
            "--config",
            str(config_path),
            "--policy",
            str(policy_path),
            "--requested-markets",
            "crypto,equities",
            "--readiness-json",
            '{"execution_quality":0.4,"reconciliation_accuracy":0.8,"open_p1_incidents":2}',
        ],
    )
    assert check_scope_governance.main() == 2
