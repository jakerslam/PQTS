#!/usr/bin/env python3
"""Validate Python-first stack direction and UI/runtime coherence contracts."""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path
from typing import Any


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyproject", default="pyproject.toml")
    parser.add_argument("--compose", default="docker-compose.yml")
    parser.add_argument("--web-package", default="apps/web/package.json")
    parser.add_argument("--stack-policy", default="config/language/stack_policy.json")
    return parser


def _load_pyproject(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _norm_pkg_name(spec: str) -> str:
    token = str(spec).strip().split(";", 1)[0].strip()
    for delim in ("==", ">=", "<=", "~=", "!=", "<", ">"):
        if delim in token:
            token = token.split(delim, 1)[0].strip()
            break
    return token.lower().replace("_", "-")


def _as_pkg_set(items: list[str]) -> set[str]:
    return {_norm_pkg_name(item) for item in items}


def _must_contain(packages: set[str], required: set[str], *, label: str) -> None:
    missing = sorted(required - packages)
    if missing:
        raise ValueError(f"{label} missing required packages: {missing}")


def validate_stack_direction(
    *,
    pyproject_path: Path,
    compose_path: Path,
    web_package_path: Path,
    stack_policy_path: Path,
) -> dict[str, Any]:
    policy = json.loads(stack_policy_path.read_text(encoding="utf-8"))
    primary_language = str(policy.get("primary_language", "")).strip().lower()
    if primary_language != "python":
        raise ValueError("stack policy primary_language must be python")
    rewrite = dict(policy.get("rewrite_policy") or {})
    if bool(rewrite.get("allow_full_native_rewrite", True)):
        raise ValueError("stack policy must forbid full native rewrite")
    native_langs = {str(token).strip().lower() for token in list(policy.get("native_kernel_languages") or [])}
    if "rust" not in native_langs:
        raise ValueError("stack policy must include rust as native hotpath language")

    payload = _load_pyproject(pyproject_path)
    project = dict(payload.get("project") or {})
    deps = [str(item) for item in list(project.get("dependencies") or [])]
    dep_names = _as_pkg_set(deps)

    _must_contain(dep_names, {"dash", "fastapi", "pydantic"}, label="project.dependencies")
    if "streamlit" in dep_names:
        raise ValueError("streamlit must not be in project.dependencies (use optional legacy_ui extra)")

    optional = dict(project.get("optional-dependencies") or {})
    analytics = _as_pkg_set([str(item) for item in list(optional.get("analytics") or [])])
    legacy_ui = _as_pkg_set([str(item) for item in list(optional.get("legacy_ui") or [])])
    native = _as_pkg_set([str(item) for item in list(optional.get("native") or [])])

    _must_contain(analytics, {"duckdb", "polars", "pyarrow"}, label="project.optional-dependencies.analytics")
    _must_contain(legacy_ui, {"streamlit"}, label="project.optional-dependencies.legacy_ui")
    _must_contain(native, {"maturin"}, label="project.optional-dependencies.native")

    compose_text = compose_path.read_text(encoding="utf-8").lower()
    if "streamlit" in compose_text:
        raise ValueError("docker-compose runtime contains streamlit; expected dash-only runtime path")

    web_package = json.loads(web_package_path.read_text(encoding="utf-8"))
    web_deps = _as_pkg_set([f"{k}=={v}" for k, v in dict(web_package.get("dependencies") or {}).items()])
    _must_contain(web_deps, {"next", "react", "react-dom"}, label="apps/web dependencies")

    return {
        "validated": True,
        "stack_policy": str(stack_policy_path),
        "core_dependencies": sorted(dep_names),
        "analytics_extra": sorted(analytics),
        "legacy_ui_extra": sorted(legacy_ui),
        "native_extra": sorted(native),
        "web_dependency_count": len(web_deps),
    }


def main() -> int:
    args = build_arg_parser().parse_args()
    report = validate_stack_direction(
        pyproject_path=Path(args.pyproject),
        compose_path=Path(args.compose),
        web_package_path=Path(args.web_package),
        stack_policy_path=Path(args.stack_policy),
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
