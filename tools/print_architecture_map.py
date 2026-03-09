"""Print a lightweight architecture map for fast human/AI traversal."""

from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from pathlib import Path

CANONICAL = ("app", "contracts", "modules", "adapters")
LEGACY = (
    "core",
    "execution",
    "analytics",
    "risk",
    "strategies",
    "markets",
    "portfolio",
    "positioning",
    "backtesting",
)
TRACKED = set(CANONICAL + LEGACY)


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
            targets.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                targets.append(node.module)

    return targets


def _count_python_files(root: Path, package: str) -> int:
    return len(_iter_python_files(root, package))


def build_import_graph(root: Path) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = defaultdict(set)

    for source in CANONICAL:
        for file_path in _iter_python_files(root, source):
            for target in _iter_import_targets(file_path):
                root_name = target.split(".", 1)[0]
                if root_name in TRACKED and root_name != source:
                    graph[source].add(root_name)

    return graph


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root path.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    print("PQTS Architecture Map")
    print("=" * 60)
    print("Canonical Layers")
    for package in CANONICAL:
        print(f"- {package}: {_count_python_files(root, package)} files")

    print("\nLegacy Domain Packages")
    for package in LEGACY:
        print(f"- {package}: {_count_python_files(root, package)} files")

    graph = build_import_graph(root)
    print("\nCanonical Import Edges")
    for source in CANONICAL:
        targets = sorted(graph.get(source, set()))
        if not targets:
            print(f"- {source} -> (none)")
        else:
            print(f"- {source} -> {', '.join(targets)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
