#!/usr/bin/env python3
"""Validate FastAPI control-plane endpoints required by active surfaces."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.append(str(SRC_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surface-contract", default="config/surfaces/surface_contract.json")
    parser.add_argument("--api-base-url", default="http://localhost:8000")
    return parser


def _collect_http_routes() -> list[str]:
    from services.api.app import create_app

    app = create_app()
    routes: list[str] = []
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if not path or not methods:
            continue
        if "GET" in methods or "POST" in methods or "PUT" in methods or "DELETE" in methods:
            routes.append(str(path))
    return routes


def main() -> int:
    from contracts.control_plane_contract import (
        ControlPlaneContract,
        validate_control_plane_contract,
    )

    args = build_arg_parser().parse_args()
    payload = json.loads(Path(args.surface_contract).read_text(encoding="utf-8"))
    mappings = payload.get("action_mappings", [])
    action_endpoints = tuple(
        str(row.get("api_endpoint", "")).strip() for row in mappings if str(row.get("api_endpoint", "")).strip()
    )

    contract = ControlPlaneContract(
        base_url=str(args.api_base_url),
        required_health_endpoints=("/health", "/ready"),
        required_action_endpoints=action_endpoints,
    )

    report = validate_control_plane_contract(
        contract=contract,
        available_routes=_collect_http_routes(),
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
