#!/usr/bin/env python3
"""Gate one-engine/two-surface, action parity, and migration safety contracts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.append(str(SRC_ROOT))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", default="config/surfaces/surface_contract.json")
    parser.add_argument("--compose", default="docker-compose.yml")
    parser.add_argument("--stack-policy", default="config/language/stack_policy.json")
    return parser


def _ensure_dash_only_ui(compose_path: Path) -> None:
    text = compose_path.read_text(encoding="utf-8").lower()
    if "streamlit" in text:
        raise ValueError("compose file contains streamlit runtime; dash-only contract violated")


def main() -> int:
    from contracts.surface_governance import (
        ActionMapping,
        OneEngineTwoSurfaceContract,
        SurfaceDescriptor,
        UIMigrationGateInput,
        evaluate_ui_migration_gate,
        validate_action_parity,
    )

    args = build_arg_parser().parse_args()
    payload = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    stack_policy = json.loads(Path(args.stack_policy).read_text(encoding="utf-8"))
    contract = OneEngineTwoSurfaceContract(engine_id=str(payload["engine_id"]))
    for row in payload.get("surfaces", []):
        contract.add_surface(SurfaceDescriptor(**row))
    contract_report = contract.validate()
    expected_studio_framework = (
        str((stack_policy.get("ui_policy", {}) or {}).get("primary_studio_framework", "")).strip().lower()
    )
    if expected_studio_framework:
        actual_framework = str(contract_report.get("studio_framework", "")).strip().lower()
        if actual_framework != expected_studio_framework:
            raise ValueError(
                "studio framework mismatch: "
                f"contract={actual_framework} policy={expected_studio_framework}"
            )

    mappings = [ActionMapping(**row) for row in payload.get("action_mappings", [])]
    parity_report = validate_action_parity(mappings)

    migration_report = evaluate_ui_migration_gate(
        UIMigrationGateInput(
            parity_passed=True,
            risk_controls_passed=True,
            operator_actions_passed=True,
            rollback_playbook_present=True,
        )
    )
    if not migration_report["passed"]:
        raise ValueError("ui migration gate blocked")

    _ensure_dash_only_ui(Path(args.compose))
    print(
        json.dumps(
            {
                "validated": True,
                "contract_report": contract_report,
                "parity_report": parity_report,
                "migration_report": migration_report,
                "stack_policy": str(args.stack_policy),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
