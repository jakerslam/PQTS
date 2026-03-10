#!/usr/bin/env python3
"""Validate Core professional surface contracts (COMP-8)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compose", default="docker-compose.yml")
    parser.add_argument(
        "--required-scripts",
        default=(
            "scripts/run_event_replay.py,"
            "scripts/run_reconciliation_daemon.py,"
            "scripts/run_canary_ramp.py,"
            "scripts/calibration_diagnostics_report.py"
        ),
    )
    return parser


def _collect_routes() -> set[str]:
    from services.api.app import create_app

    app = create_app()
    out: set[str] = set()
    for route in app.routes:
        path = getattr(route, "path", "")
        if path:
            out.add(str(path))
    return out


def main() -> int:
    args = build_arg_parser().parse_args()
    compose_path = Path(args.compose)
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8")) or {}
    services = (compose.get("services") or {}) if isinstance(compose, dict) else {}

    missing_services = [name for name in ("app", "dashboard") if name not in services]
    if missing_services:
        raise SystemExit(f"missing required compose services: {missing_services}")

    required_scripts = [token.strip() for token in str(args.required_scripts).split(",") if token.strip()]
    missing_scripts = [path for path in required_scripts if not Path(path).exists()]
    if missing_scripts:
        raise SystemExit(f"missing required core scripts: {missing_scripts}")

    routes = _collect_routes()
    required_routes = {
        "/v1/execution/orders",
        "/v1/execution/fills",
        "/v1/pnl/snapshots",
        "/v1/risk/state/{account_id}",
        "/ws/orders",
        "/ws/risk",
    }
    missing_routes = sorted(route for route in required_routes if route not in routes)
    if missing_routes:
        raise SystemExit(f"missing required API/WS routes: {missing_routes}")

    payload = {
        "validated": True,
        "required_scripts": required_scripts,
        "api_route_count": len(routes),
        "required_route_count": len(required_routes),
        "compose_services": sorted(services.keys()),
    }
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
