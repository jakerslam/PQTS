#!/usr/bin/env python3
"""Validate wedge-first market scope governance (COMP-10)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.append(str(SRC_ROOT))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/paper.yaml")
    parser.add_argument("--policy", default="config/governance/market_scope_policy.json")
    parser.add_argument("--requested-markets", default="crypto")
    parser.add_argument(
        "--readiness-json",
        default="",
        help="Inline JSON payload with readiness metrics (execution_quality, reconciliation_accuracy, open_p1_incidents).",
    )
    return parser


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return dict(data or {})


def main() -> int:
    from core.market_scope_governance import (
        evaluate_market_scope_request,
        resolve_market_scope_policy,
    )

    args = build_arg_parser().parse_args()
    config_path = Path(args.config)
    policy_path = Path(args.policy)

    cfg = _load_yaml(config_path)
    runtime = cfg.get("runtime", {})
    if not isinstance(runtime, dict):
        runtime = {}
    cfg["runtime"] = runtime

    policy_payload = json.loads(policy_path.read_text(encoding="utf-8"))
    runtime["market_scope_policy"] = policy_payload

    policy = resolve_market_scope_policy(cfg)
    requested = [token.strip() for token in str(args.requested_markets).split(",") if token.strip()]
    readiness = json.loads(args.readiness_json) if str(args.readiness_json).strip() else {}
    report = evaluate_market_scope_request(
        policy=policy,
        requested_markets=requested,
        readiness=readiness,
    )

    print(json.dumps(report, sort_keys=True))
    return 0 if bool(report.get("passed")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
