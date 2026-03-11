#!/usr/bin/env python3
"""Fail when release instruction examples hardcode stale semver tags.

Allowed examples:
- `vX.Y.Z` (preferred placeholder)
- `v<current_pyproject_version>`
"""

from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path

_TAG_RE = re.compile(r"\bv(\d+\.\d+\.\d+)\b")


def _current_version(pyproject_path: Path) -> str:
    payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = payload.get("project", {})
    if not isinstance(project, dict):
        return ""
    return str(project.get("version", "")).strip()


def _check_file(path: Path, current_version: str) -> list[str]:
    errors: list[str] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if "for example" not in line.lower() and "example" not in line.lower():
            continue
        if "vX.Y.Z" in line or "v<current_version>" in line:
            continue
        for tag in _TAG_RE.findall(line):
            if tag != current_version:
                errors.append(
                    f"{path}:{line_no} stale release example tag v{tag} (expected v{current_version} or vX.Y.Z)"
                )
    return errors


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyproject", default="pyproject.toml")
    parser.add_argument(
        "--files",
        nargs="+",
        default=["README.md", "docs/RELEASE_CHECKLIST.md", "docs/QUICKSTART_5_MIN.md"],
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    version = _current_version(Path(args.pyproject))
    if not version:
        print("FAIL unable to resolve project version from pyproject.toml")
        return 2

    errors: list[str] = []
    for file_str in args.files:
        path = Path(file_str)
        if not path.exists():
            continue
        errors.extend(_check_file(path, version))

    if errors:
        for err in errors:
            print(f"FAIL {err}")
        print(f"Release example validation failed: {len(errors)} issue(s)")
        return 2
    print(f"PASS release examples use current version v{version} or placeholders")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
