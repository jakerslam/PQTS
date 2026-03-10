#!/usr/bin/env python3
"""Wallet-mode example runner for integration onboarding."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

MODE_CONFIG: dict[str, dict[str, Any]] = {
    "eoa": {
        "description": "Direct EOA signing mode.",
        "required_env": ["POLYMARKET_PRIVATE_KEY"],
        "signature_type": "eoa",
    },
    "proxy": {
        "description": "Proxy wallet mode with separate funder address.",
        "required_env": ["POLYMARKET_PRIVATE_KEY", "POLYMARKET_FUNDER"],
        "signature_type": "proxy",
    },
    "safe": {
        "description": "Safe wallet mode (browser-wallet compatible signer).",
        "required_env": ["POLYMARKET_PRIVATE_KEY", "POLYMARKET_FUNDER"],
        "signature_type": "safe",
    },
}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=sorted(MODE_CONFIG), required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", choices=["table", "json"], default="table")
    return parser


def _emit(mode: str, payload: dict[str, Any], output: str) -> None:
    if output == "json":
        print(json.dumps({"mode": mode, **payload}, sort_keys=True))
        return
    print(f"Mode: {mode}")
    for key, value in payload.items():
        print(f"{key}: {value}")


def run(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    mode = str(args.mode)
    cfg = MODE_CONFIG[mode]
    required_env = list(cfg["required_env"])
    missing = [name for name in required_env if not str(os.getenv(name, "")).strip()]

    payload: dict[str, Any] = {
        "description": cfg["description"],
        "signature_type": cfg["signature_type"],
        "required_env": required_env,
        "missing_env": missing,
        "dry_run": bool(args.dry_run),
    }

    if args.dry_run:
        _emit(mode, payload, args.output)
        return 0

    if missing:
        payload["error"] = f"missing required env vars: {', '.join(missing)}"
        _emit(mode, payload, args.output)
        return 2

    payload["status"] = "ready_for_authenticated_flow"
    _emit(mode, payload, args.output)
    return 0


def main() -> int:
    return run(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
