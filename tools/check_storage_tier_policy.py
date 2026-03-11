#!/usr/bin/env python3
"""Check storage-tier boundaries for configured data paths."""

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
    parser.add_argument("--config", default="config/paper.yaml")
    parser.add_argument("--runtime-state", default="data/engine_state.json")
    parser.add_argument("--analytics-root", default="data/analytics")
    parser.add_argument("--lake-root", default="data/lake")
    return parser


def main() -> int:
    from research.analytics_data_plane import validate_storage_tier_boundary

    args = build_arg_parser().parse_args()
    checks = [
        ("local_analytics", str(args.lake_root)),
        ("operational_state", str(args.analytics_root)),
        ("operational_state", str(args.runtime_state)),
    ]
    for expected, path in checks:
        validate_storage_tier_boundary(path=path, expected_tier=expected)
    print(json.dumps({"validated": True, "checks": checks}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
