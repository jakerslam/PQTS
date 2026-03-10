#!/usr/bin/env python3
"""Enforce benchmark bundle governance and reference-pack diff artifacts."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

_BUNDLE_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_.+$")


def _load_json(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _latest(globbed: list[Path]) -> Path | None:
    if not globbed:
        return None
    return sorted(globbed)[-1]


def _required_bundle_paths(bundle: Path) -> dict[str, Path | None]:
    return {
        "readme": bundle / "README.md",
        "config_snapshot": bundle / "config_paper_snapshot.yaml",
        "dataset_manifest": bundle / "dataset_manifest.json",
        "suite": _latest(list(bundle.glob("simulation_suite_*.json"))),
        "leaderboard": _latest(list(bundle.glob("simulation_leaderboard_*.csv"))),
    }


def _extract_rows_from_suite(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    results = payload.get("results")
    if isinstance(results, list):
        for item in results:
            if not isinstance(item, Mapping):
                continue
            scenario = item.get("scenario")
            scenario = scenario if isinstance(scenario, Mapping) else {}
            rows.append(
                {
                    "market": str(scenario.get("market") or "unknown"),
                    "strategy": str(scenario.get("strategy") or "unknown"),
                    "quality": float(item.get("quality_score", 0.0) or 0.0),
                    "fill_rate": _fill_rate(item),
                    "reject_rate": float(item.get("reject_rate", 0.0) or 0.0),
                }
            )
    if rows:
        return rows
    leaderboard = payload.get("leaderboard")
    if isinstance(leaderboard, list):
        for item in leaderboard:
            if not isinstance(item, Mapping):
                continue
            rows.append(
                {
                    "market": str(item.get("market") or "unknown"),
                    "strategy": str(item.get("strategy") or "unknown"),
                    "quality": float(item.get("avg_quality_score", 0.0) or 0.0),
                    "fill_rate": float(item.get("avg_fill_rate", 0.0) or 0.0),
                    "reject_rate": float(item.get("avg_reject_rate", 0.0) or 0.0),
                }
            )
    return rows


def _fill_rate(result: Mapping[str, Any]) -> float:
    submitted = float(result.get("submitted", 0.0) or 0.0)
    if submitted <= 0.0:
        return 0.0
    return float((float(result.get("filled", 0.0) or 0.0)) / submitted)


def _deterministic_generated_at(index_rows: list[dict[str, Any]]) -> str:
    timestamps = [str(row.get("run_timestamp", "")).strip() for row in index_rows]
    timestamps = [token for token in timestamps if token]
    if timestamps:
        return sorted(timestamps)[-1]
    return datetime(1970, 1, 1, tzinfo=timezone.utc).isoformat()


def _bundle_sort_key(name: str) -> str:
    return name


def validate_and_build_reference_artifacts(
    *,
    results_dir: str | Path,
    min_reference_packs: int = 3,
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    root = Path(results_dir)
    if not root.exists():
        return [f"results_dir does not exist: {root}"], [], []

    errors: list[str] = []
    index_rows: list[dict[str, Any]] = []
    latest_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    previous_by_key: dict[tuple[str, str], dict[str, Any]] = {}

    bundles = [
        child
        for child in sorted(root.iterdir())
        if child.is_dir() and _BUNDLE_NAME_RE.match(child.name)
    ]
    if len(bundles) < min_reference_packs:
        errors.append(
            f"expected at least {min_reference_packs} reference packs; found {len(bundles)}"
        )

    for bundle in bundles:
        required = _required_bundle_paths(bundle)
        for field, path in required.items():
            if path is None or not path.exists():
                errors.append(f"{bundle.name}: missing required artifact '{field}'")
        if any(path is None or not path.exists() for path in required.values()):
            continue

        assert required["dataset_manifest"] is not None
        manifest = _load_json(required["dataset_manifest"])
        for key in ("schema_version", "dataset_version", "generated_at", "sources"):
            if key not in manifest:
                errors.append(f"{bundle.name}: dataset_manifest missing key '{key}'")
        if "sources" in manifest and not isinstance(manifest.get("sources"), list):
            errors.append(f"{bundle.name}: dataset_manifest.sources must be a list")

        assert required["suite"] is not None
        suite_payload = _load_json(required["suite"])
        if not suite_payload.get("created_at"):
            errors.append(f"{bundle.name}: suite payload missing created_at")

        rows = _extract_rows_from_suite(suite_payload)
        if not rows:
            errors.append(f"{bundle.name}: no scenario rows found in suite payload")
            continue

        for row in rows:
            key = (str(row["market"]), str(row["strategy"]))
            pack = {
                "bundle_name": bundle.name,
                "run_timestamp": str(suite_payload.get("created_at") or ""),
                "dataset_version": str(manifest.get("dataset_version") or ""),
                "market": key[0],
                "strategy": key[1],
                "quality": float(row["quality"]),
                "fill_rate": float(row["fill_rate"]),
                "reject_rate": float(row["reject_rate"]),
                "result_class": "reference"
                if float(row["fill_rate"]) > 0.0 and float(row["reject_rate"]) <= 0.40
                else "diagnostic_only",
            }
            index_rows.append(pack)

            prev = latest_by_key.get(key)
            if prev is None or _bundle_sort_key(pack["bundle_name"]) > _bundle_sort_key(
                prev["bundle_name"]
            ):
                if prev is not None:
                    previous_by_key[key] = prev
                latest_by_key[key] = pack

    diffs: list[dict[str, Any]] = []
    for key, latest in sorted(latest_by_key.items(), key=lambda item: item[0]):
        previous = previous_by_key.get(key)
        if previous is None:
            continue
        diffs.append(
            {
                "market": key[0],
                "strategy": key[1],
                "latest_bundle": latest["bundle_name"],
                "previous_bundle": previous["bundle_name"],
                "delta_quality": round(float(latest["quality"]) - float(previous["quality"]), 8),
                "delta_fill_rate": round(
                    float(latest["fill_rate"]) - float(previous["fill_rate"]), 8
                ),
                "delta_reject_rate": round(
                    float(latest["reject_rate"]) - float(previous["reject_rate"]), 8
                ),
            }
        )
    return errors, sorted(index_rows, key=lambda row: (row["bundle_name"], row["market"], row["strategy"])), diffs


def write_reference_artifacts(
    *,
    index_rows: list[dict[str, Any]],
    diffs: list[dict[str, Any]],
    index_out: str | Path,
    diff_out: str | Path,
) -> tuple[Path, Path]:
    index_path = Path(index_out)
    diff_path = Path(diff_out)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    diff_path.parent.mkdir(parents=True, exist_ok=True)

    generated_at = _deterministic_generated_at(index_rows)
    index_payload = {
        "generated_at": generated_at,
        "pack_count": len(index_rows),
        "packs": index_rows,
    }
    diff_payload = {
        "generated_at": generated_at,
        "diff_count": len(diffs),
        "diffs": diffs,
    }
    index_path.write_text(json.dumps(index_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    diff_path.write_text(json.dumps(diff_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return index_path, diff_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--index-out", default="data/reports/reference_packs/index.json")
    parser.add_argument("--diff-out", default="data/reports/reference_packs/diff.json")
    parser.add_argument("--min-reference-packs", type=int, default=3)
    parser.add_argument("--validate-only", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    errors, index_rows, diffs = validate_and_build_reference_artifacts(
        results_dir=args.results_dir,
        min_reference_packs=int(args.min_reference_packs),
    )

    if not args.validate_only:
        index_path, diff_path = write_reference_artifacts(
            index_rows=index_rows,
            diffs=diffs,
            index_out=args.index_out,
            diff_out=args.diff_out,
        )
        print(f"WROTE {index_path}")
        print(f"WROTE {diff_path}")

    if errors:
        for item in errors:
            print(f"FAIL {item}")
        print(f"Validation failed with {len(errors)} issue(s).")
        return 2

    print(
        f"PASS bundle governance: {len(index_rows)} strategy-pack rows, {len(diffs)} diff rows."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
