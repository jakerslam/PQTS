"""Validate canonical architecture layer import boundaries.

This checker only enforces boundaries for the new canonical layers:
- contracts
- adapters
- modules
- app
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

CANONICAL_PACKAGES = ("contracts", "adapters", "modules", "app")
ALLOWED_IMPORTS: dict[str, set[str]] = {
    "contracts": {"contracts"},
    "adapters": {"contracts", "adapters"},
    "modules": {"contracts", "adapters", "modules"},
    "app": {"contracts", "adapters", "modules", "app"},
}


def _module_name_for_file(root: Path, file_path: Path) -> str:
    relative = file_path.relative_to(root)
    return ".".join(relative.with_suffix("").parts)


def _iter_python_files(root: Path, package: str) -> list[Path]:
    package_path = root / package
    if not package_path.exists():
        return []
    return sorted(path for path in package_path.rglob("*.py") if path.is_file())


def _iter_import_targets(file_path: Path) -> list[str]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    targets: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                targets.append(node.module)

    return targets


def collect_boundary_violations(root: Path) -> list[str]:
    violations: list[str] = []

    for package in CANONICAL_PACKAGES:
        allowed = ALLOWED_IMPORTS[package]
        for file_path in _iter_python_files(root, package):
            module_name = _module_name_for_file(root, file_path)
            for target in _iter_import_targets(file_path):
                target_root = target.split(".", 1)[0]
                if target_root not in CANONICAL_PACKAGES:
                    continue
                if target_root not in allowed:
                    violations.append(
                        f"{module_name}: forbidden import '{target}' for layer '{package}'"
                    )

    return sorted(set(violations))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root path (default: current directory).",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    violations = collect_boundary_violations(root)

    if violations:
        print("Architecture boundary violations detected:")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("Architecture boundary check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
