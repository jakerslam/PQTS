#!/usr/bin/env python3
"""Run trust-surface validation checks and persist a machine-readable report."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any


CHECKS: tuple[tuple[str, list[str]], ...] = (
    ("truth_surface", ["python3", "tools/check_truth_surface.py"]),
    (
        "integration_claim_parity",
        [
            "python3",
            "tools/check_integration_claim_parity.py",
            "--readme",
            "README.md",
            "--index",
            "config/integrations/official_integrations.json",
        ],
    ),
    (
        "benchmark_program",
        [
            "python3",
            "tools/check_benchmark_program.py",
            "--reference-performance",
            "results/reference_performance_latest.json",
            "--results-root",
            ".",
            "--policy",
            "config/benchmarks/program_policy.json",
            "--report-out",
            "data/reports/benchmark_program/latest.json",
        ],
    ),
    (
        "reference_performance_contract",
        [
            "python3",
            "tools/check_reference_performance_contract.py",
            "--reference-performance",
            "results/reference_performance_latest.json",
        ],
    ),
    (
        "external_validation_evidence",
        [
            "python3",
            "tools/check_external_validation_evidence.py",
            "--user-research",
            "docs/USER_RESEARCH_2026_03.md",
            "--readme",
            "README.md",
        ],
    ),
    (
        "external_beta_framework",
        [
            "python3",
            "tools/check_external_beta_framework.py",
            "--registry",
            "data/validation/external_beta/cohort_registry.json",
            "--user-research",
            "docs/USER_RESEARCH_2026_03.md",
        ],
    ),
    ("source_reliability", ["python3", "tools/check_source_reliability.py"]),
    ("web_api_contracts", ["python3", "tools/check_web_api_contracts.py"]),
    ("surface_contracts", ["python3", "tools/check_surface_contracts.py"]),
    (
        "release_examples",
        [
            "python3",
            "tools/check_release_examples.py",
            "--pyproject",
            "pyproject.toml",
            "--files",
            "README.md",
            "docs/RELEASE_CHECKLIST.md",
            "docs/QUICKSTART_5_MIN.md",
        ],
    ),
)


def run_command(command: list[str]) -> dict[str, Any]:
    started = time.time()
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    duration_ms = round((time.time() - started) * 1000, 2)
    return {
        "command": command,
        "returncode": int(completed.returncode),
        "duration_ms": duration_ms,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "passed": completed.returncode == 0,
    }


def run_suite(checks: tuple[tuple[str, list[str]], ...] = CHECKS) -> dict[str, Any]:
    results: dict[str, dict[str, Any]] = {}
    for name, command in checks:
        results[name] = run_command(command)

    failures = [name for name, row in results.items() if not bool(row.get("passed"))]
    return {
        "generated_at_epoch": int(time.time()),
        "passed": not failures,
        "failure_count": len(failures),
        "failures": failures,
        "results": results,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default="data/reports/validation/trust_surface_latest.json",
        help="Output JSON report path.",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    report = run_suite()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out_path), "passed": report["passed"], "failure_count": report["failure_count"]}))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
