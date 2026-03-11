#!/usr/bin/env python3
"""Validate native hot-path skeleton and release matrix metadata."""

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
    parser.add_argument("--cargo", default="native/hotpath/Cargo.toml")
    parser.add_argument("--lib", default="native/hotpath/src/lib.rs")
    parser.add_argument("--matrix", default="config/native/release_matrix.json")
    parser.add_argument("--policy", default="config/native/migration_policy.json")
    parser.add_argument("--module", default="pqts_hotpath")
    return parser


def main() -> int:
    from core.native_migration import build_native_release_matrix, load_migration_policy

    args = build_arg_parser().parse_args()
    cargo = Path(args.cargo)
    lib = Path(args.lib)
    matrix = Path(args.matrix)
    policy_path = Path(args.policy)
    for path in (cargo, lib, matrix, policy_path):
        if not path.exists():
            raise SystemExit(f"missing required native artifact: {path}")

    policy = load_migration_policy(policy_path)
    required_priority = {"orderbook_sequence", "event_replay", "risk_aware_router"}
    missing_priority = sorted(required_priority.difference(set(policy.priority_modules)))
    if missing_priority:
        raise SystemExit(f"migration policy missing priority modules: {missing_priority}")

    payload = json.loads(matrix.read_text(encoding="utf-8"))
    expected = build_native_release_matrix(str(args.module))
    actual_rows = payload.get("artifacts", [])
    if len(actual_rows) != len(expected):
        raise SystemExit(
            f"release matrix mismatch: expected {len(expected)} rows, found {len(actual_rows)}"
        )

    lib_text = lib.read_text(encoding="utf-8")
    required_snippets = [
        "fn sum_notional(",
        "wrap_pyfunction!(sum_notional, m)",
        "fn fill_metrics(",
        "wrap_pyfunction!(fill_metrics, m)",
        "fn sequence_transition(",
        "wrap_pyfunction!(sequence_transition, m)",
        "fn uniform_from_seed(",
        "wrap_pyfunction!(uniform_from_seed, m)",
        "fn event_id_hash(",
        "wrap_pyfunction!(event_id_hash, m)",
        "fn paper_fill_metrics(",
        "wrap_pyfunction!(paper_fill_metrics, m)",
        "fn smart_router_score(",
        "wrap_pyfunction!(smart_router_score, m)",
        "fn quote_state(",
        "wrap_pyfunction!(quote_state, m)",
        "fn version()",
        "wrap_pyfunction!(version, m)",
    ]
    missing = [snippet for snippet in required_snippets if snippet not in lib_text]
    if missing:
        raise SystemExit(f"native lib is missing required symbols: {missing}")

    print(
        json.dumps(
                {
                    "validated": True,
                    "rows": len(actual_rows),
                    "module": args.module,
                    "policy": str(policy_path),
                "required_symbols": [
                    "sum_notional",
                    "fill_metrics",
                    "sequence_transition",
                    "uniform_from_seed",
                    "event_id_hash",
                    "paper_fill_metrics",
                    "smart_router_score",
                    "quote_state",
                    "version",
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
