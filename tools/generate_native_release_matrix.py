#!/usr/bin/env python3
"""Generate or verify native hot-path release matrix metadata."""

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
    parser.add_argument("--module", default="pqts_hotpath")
    parser.add_argument("--out", default="config/native/release_matrix.json")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify existing file matches generated payload.",
    )
    return parser


def _render_payload(module: str) -> dict[str, object]:
    from core.native_migration import build_native_release_matrix

    rows = build_native_release_matrix(module)
    return {
        "module": module,
        "artifacts": [
            {
                "target": row.target,
                "python_version": row.python_version,
                "wheel_tag": row.wheel_tag,
            }
            for row in rows
        ],
    }


def main() -> int:
    args = build_arg_parser().parse_args()
    out_path = Path(args.out)
    payload = _render_payload(str(args.module))
    rendered = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    if args.check:
        if not out_path.exists():
            raise SystemExit(f"missing matrix file: {out_path}")
        current = out_path.read_text(encoding="utf-8")
        if current != rendered:
            raise SystemExit(
                f"native release matrix drift detected in {out_path}. "
                "Run tools/generate_native_release_matrix.py to refresh."
            )
    else:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
    print(
        json.dumps(
            {
                "module": str(args.module),
                "out": str(out_path),
                "check": bool(args.check),
                "artifact_count": len(payload["artifacts"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
