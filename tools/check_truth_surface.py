#!/usr/bin/env python3
"""Validate distribution/docs/runtime truth-surface consistency contracts.

Covers SRS requirements:
- COMP-15 (distribution/install-path truth)
- COMP-16 (version + maturity consistency)
- LANG-13 (dashboard runtime safety/port consistency)
- LANG-14 (public surface canonicalization markers)
"""

from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path
from typing import Any

_PIP_INSTALL_RE = re.compile(r"^\s*pip\s+install\s+([A-Za-z0-9_.-]+)(?:\s|$)")
_PQTS_VERSION_BANNER_RE = re.compile(r"\bPQTS\s+v(\d+\.\d+\.\d+)\b", flags=re.IGNORECASE)
_PRODUCTION_READY_RE = re.compile(r"\bproduction-ready\b", flags=re.IGNORECASE)
_PORT_LITERAL_RE = re.compile(r"\b(?:port\s*=\s*|localhost:)(\d{2,5})\b")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _load_policy(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("truth-surface policy must be a JSON object")
    return payload


def _load_pyproject_version(pyproject_path: Path) -> str:
    payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = payload.get("project") or {}
    if not isinstance(project, dict):
        return ""
    return str(project.get("version") or "").strip()


def _non_comment_install_lines(text: str, package: str) -> list[str]:
    hits: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _PIP_INSTALL_RE.match(line)
        if not match:
            continue
        if match.group(1).strip().lower() == package.lower():
            hits.append(line)
    return hits


def evaluate_truth_surface(
    *,
    policy_path: Path,
    pyproject_path: Path,
    readme_path: Path,
    quickstart_path: Path,
    development_summary_path: Path,
    dashboard_app_path: Path,
    dashboard_start_path: Path,
) -> list[str]:
    policy = _load_policy(policy_path)
    errors: list[str] = []

    canonical_version = str(policy.get("canonical_release_version") or "").strip()
    maturity = str(policy.get("maturity") or "").strip().lower()
    pyproject_version = _load_pyproject_version(pyproject_path)

    if not canonical_version:
        errors.append("policy missing canonical_release_version")
    if canonical_version and pyproject_version != canonical_version:
        errors.append(
            f"pyproject version mismatch: expected {canonical_version}, found {pyproject_version or 'missing'}"
        )

    readme = _read_text(readme_path)
    quickstart = _read_text(quickstart_path)
    development_summary = _read_text(development_summary_path)

    if maturity == "alpha":
        for label, text in (
            ("README", readme),
            ("QUICKSTART_5_MIN", quickstart),
            ("DEVELOPMENT_SUMMARY", development_summary),
        ):
            if _PRODUCTION_READY_RE.search(text):
                errors.append(f"{label}: contains forbidden maturity phrase 'production-ready' for alpha release")

    for label, text in (
        ("README", readme),
        ("DEVELOPMENT_SUMMARY", development_summary),
    ):
        for token in _PQTS_VERSION_BANNER_RE.findall(text):
            if canonical_version and token != canonical_version:
                errors.append(
                    f"{label}: version banner mismatch '{token}' (expected {canonical_version})"
                )

    distribution = dict(policy.get("distribution") or {})
    pypi = dict(distribution.get("pypi") or {})
    package_name = str(pypi.get("package") or "pqts").strip() or "pqts"
    pypi_available = bool(pypi.get("available", False))
    if not pypi_available:
        for label, text in (("README", readme), ("QUICKSTART_5_MIN", quickstart)):
            hits = _non_comment_install_lines(text, package_name)
            if hits:
                errors.append(
                    f"{label}: unqualified install commands present while pypi.available=false: {hits[:2]}"
                )

    ui = dict(policy.get("ui_surface") or {})
    required_markers = [str(x).strip() for x in list(ui.get("required_markers") or []) if str(x).strip()]
    for marker in required_markers:
        if marker not in readme:
            errors.append(f"README missing required UI marker: {marker}")
    quickstart_markers = [
        str(x).strip() for x in list(ui.get("quickstart_required_markers") or []) if str(x).strip()
    ]
    for marker in quickstart_markers:
        if marker not in quickstart:
            errors.append(f"QUICKSTART_5_MIN missing required UI marker: {marker}")
    if pypi_available:
        package_markers = [
            str(x).strip() for x in list(ui.get("quickstart_package_markers") or []) if str(x).strip()
        ]
        for marker in package_markers:
            if marker not in quickstart:
                errors.append(f"QUICKSTART_5_MIN missing required package-first marker: {marker}")

    dashboard_port = int(ui.get("dashboard_port", 8501))
    dashboard_start = _read_text(dashboard_start_path)
    if f"port={dashboard_port}" not in dashboard_start:
        errors.append(f"dashboard start path must run on port {dashboard_port}")

    dashboard_app = _read_text(dashboard_app_path)
    main_block = dashboard_app.split("if __name__ == \"__main__\":", 1)
    if len(main_block) != 2:
        errors.append("dashboard app missing __main__ block")
    else:
        tail = main_block[1]
        if f"port={dashboard_port}" not in tail:
            errors.append(f"dashboard __main__ must use port {dashboard_port}")
        if re.search(r"debug\s*=\s*True", tail):
            errors.append("dashboard __main__ must not default to debug=True")

    if bool(ui.get("forbid_external_codepen", True)) and "codepen.io" in dashboard_app.lower():
        errors.append("dashboard app includes forbidden external codepen stylesheet dependency")

    for match in _PORT_LITERAL_RE.findall(readme):
        value = int(match)
        if value == 8050:
            errors.append("README still references legacy dashboard port 8050")

    return errors


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", default="config/release/truth_surface_policy.json")
    parser.add_argument("--pyproject", default="pyproject.toml")
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--quickstart", default="docs/QUICKSTART_5_MIN.md")
    parser.add_argument("--development-summary", default="docs/DEVELOPMENT_SUMMARY.md")
    parser.add_argument("--dashboard-app", default="src/dashboard/app.py")
    parser.add_argument("--dashboard-start", default="src/dashboard/start.py")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    errors = evaluate_truth_surface(
        policy_path=Path(args.policy),
        pyproject_path=Path(args.pyproject),
        readme_path=Path(args.readme),
        quickstart_path=Path(args.quickstart),
        development_summary_path=Path(args.development_summary),
        dashboard_app_path=Path(args.dashboard_app),
        dashboard_start_path=Path(args.dashboard_start),
    )
    if errors:
        for item in errors:
            print(f"FAIL {item}")
        print(f"Truth-surface validation failed: {len(errors)} issue(s)")
        return 2
    print("PASS truth-surface validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
