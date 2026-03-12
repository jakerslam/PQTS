#!/usr/bin/env python3
"""Validate contract fields for results/reference_performance_latest.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ALLOWED_TRUST = {"reference", "diagnostic_only", "unverified"}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def evaluate_reference_performance_contract(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"missing file: {path}"]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"failed to parse json: {exc}"]

    if not isinstance(payload, dict):
        return ["top-level payload must be a JSON object"]

    for key in ("schema_version", "generated_at", "bundle_count", "trust_label", "provenance", "bundles"):
        if key not in payload:
            errors.append(f"missing top-level key: {key}")

    trust_label = str(payload.get("trust_label", "")).strip()
    if trust_label and trust_label not in ALLOWED_TRUST:
        errors.append(f"invalid top-level trust_label: {trust_label}")

    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        errors.append("top-level provenance must be an object")
    else:
        for key in ("generated_at", "generator", "source_policy", "artifact_path", "bundle_count"):
            if key not in provenance:
                errors.append(f"missing top-level provenance key: {key}")

    bundles = payload.get("bundles")
    if not isinstance(bundles, list):
        errors.append("bundles must be an array")
        return errors

    bundle_count = payload.get("bundle_count")
    if _is_number(bundle_count) and int(bundle_count) != len(bundles):
        errors.append(f"bundle_count mismatch: {bundle_count} != {len(bundles)}")

    required_summary_keys = (
        "avg_fill_rate",
        "avg_quality_score",
        "avg_reject_rate",
        "total_filled",
        "total_rejected",
        "total_submitted",
    )

    for idx, bundle in enumerate(bundles):
        if not isinstance(bundle, dict):
            errors.append(f"bundle[{idx}] must be an object")
            continue
        for key in (
            "bundle",
            "path",
            "report_path",
            "leaderboard_path",
            "markets",
            "strategies",
            "command",
            "summary",
            "trust_label",
            "provenance",
        ):
            if key not in bundle:
                errors.append(f"bundle[{idx}] missing key: {key}")

        b_trust = str(bundle.get("trust_label", "")).strip()
        if b_trust and b_trust not in ALLOWED_TRUST:
            errors.append(f"bundle[{idx}] invalid trust_label: {b_trust}")

        summary = bundle.get("summary")
        if not isinstance(summary, dict):
            errors.append(f"bundle[{idx}] summary must be an object")
        else:
            for key in required_summary_keys:
                if key not in summary:
                    errors.append(f"bundle[{idx}] summary missing key: {key}")
                elif not _is_number(summary.get(key)):
                    errors.append(f"bundle[{idx}] summary[{key}] must be numeric")

        b_provenance = bundle.get("provenance")
        if not isinstance(b_provenance, dict):
            errors.append(f"bundle[{idx}] provenance must be an object")
        else:
            for key in (
                "generated_at",
                "generator",
                "dataset_manifest_path",
                "config_snapshot_path",
                "metrics_chart_path",
            ):
                if key not in b_provenance:
                    errors.append(f"bundle[{idx}] provenance missing key: {key}")

    return errors


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reference-performance",
        default="results/reference_performance_latest.json",
        help="Path to reference performance JSON contract.",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    errors = evaluate_reference_performance_contract(Path(args.reference_performance))
    if errors:
        for item in errors:
            print(f"FAIL {item}")
        print(f"Reference performance contract validation failed: {len(errors)} issue(s)")
        return 2
    print("PASS reference performance contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
