#!/usr/bin/env python3
"""Validate tier safety baseline and entitlement policy contracts (COMP-14)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", default="config/entitlements/tier_policy.json")
    return parser


def _resolve_plan(policy_path: Path, plan: str):
    from core.multi_tenant import resolve_tenant_entitlements

    return resolve_tenant_entitlements(
        {
            "runtime": {
                "tenant": {
                    "tier_policy_path": str(policy_path),
                    "plan": plan,
                }
            }
        }
    )


def main() -> int:
    from core.multi_tenant import enforce_live_enablement_preconditions

    args = build_arg_parser().parse_args()
    policy_path = Path(args.policy)
    if not policy_path.exists():
        raise SystemExit(f"missing tier policy: {policy_path}")

    plans = {
        "community": _resolve_plan(policy_path, "community"),
        "solo_pro": _resolve_plan(policy_path, "solo_pro"),
        "team": _resolve_plan(policy_path, "team"),
        "enterprise": _resolve_plan(policy_path, "enterprise"),
    }

    if plans["community"].allow_live_trading:
        raise SystemExit("community tier must be paper-only")

    failures: list[str] = []
    for name in ("solo_pro", "team", "enterprise"):
        entitlements = plans[name]
        blocked = enforce_live_enablement_preconditions(
            entitlements=entitlements,
            runtime={"live_readiness": {"paper_ready": False, "operator_acknowledged": False}},
        )
        if blocked["passed"]:
            failures.append(f"{name}: expected live preconditions to block when readiness missing")
        allowed = enforce_live_enablement_preconditions(
            entitlements=entitlements,
            runtime={"live_readiness": {"paper_ready": True, "operator_acknowledged": True}},
        )
        if not allowed["passed"]:
            failures.append(f"{name}: expected live preconditions to pass when readiness acknowledged")

    if failures:
        raise SystemExit("; ".join(failures))

    payload = {
        "validated": True,
        "policy": str(policy_path),
        "plans": sorted(plans.keys()),
        "paper_only_plan": "community",
    }
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
