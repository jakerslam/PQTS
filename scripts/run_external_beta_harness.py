#!/usr/bin/env python3
"""Run the external beta cohort protocol and emit release-window evidence artifacts."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_WINDOW_RE = re.compile(
    r"^\s*[-*]?\s*`?release_window\s*:\s*([0-9]{4}-[0-9]{2})`?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)
_ALLOWED_PERSONA = {"beginner", "professional"}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _extract_release_window(user_research_path: Path) -> str:
    text = user_research_path.read_text(encoding="utf-8")
    match = _WINDOW_RE.search(text)
    if not match:
        raise ValueError("user research document missing `release_window: YYYY-MM` metadata")
    return str(match.group(1)).strip()


def _validate_report(payload: Any, *, expected_persona: str, path: Path) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return [f"{path}: report must be JSON object"], {}

    persona = str(payload.get("persona", "")).strip().lower()
    if persona != expected_persona:
        errors.append(f"{path}: persona must be '{expected_persona}'")
    if persona not in _ALLOWED_PERSONA:
        errors.append(f"{path}: invalid persona '{persona}'")

    participant_count = payload.get("participant_count")
    if not isinstance(participant_count, int) or participant_count < 0:
        errors.append(f"{path}: participant_count must be non-negative integer")
        participant_count = 0

    completion_rate = payload.get("task_completion_rate")
    if not isinstance(completion_rate, (int, float)) or float(completion_rate) < 0 or float(completion_rate) > 1:
        errors.append(f"{path}: task_completion_rate must be within [0, 1]")
        completion_rate = 0.0

    median_minutes = payload.get("median_time_to_first_meaningful_result_minutes")
    if not isinstance(median_minutes, (int, float)) or float(median_minutes) <= 0:
        errors.append(f"{path}: median_time_to_first_meaningful_result_minutes must be positive")
        median_minutes = 0.0

    blockers = payload.get("top_blockers")
    if not isinstance(blockers, list):
        errors.append(f"{path}: top_blockers must be an array")
        blockers = []

    channels = payload.get("channels", [])
    if not isinstance(channels, list):
        errors.append(f"{path}: channels must be an array")
        channels = []

    out = {
        "persona": persona,
        "participant_count": int(participant_count),
        "task_completion_rate": float(completion_rate),
        "median_time_to_first_meaningful_result_minutes": float(median_minutes),
        "top_blockers": [str(item).strip() for item in blockers if str(item).strip()],
        "channels": [str(item).strip() for item in channels if str(item).strip()],
        "notes": str(payload.get("notes", "")).strip(),
    }
    return errors, out


def _default_report(persona: str) -> dict[str, Any]:
    return {
        "persona": persona,
        "participant_count": 0,
        "task_completion_rate": 0.0,
        "median_time_to_first_meaningful_result_minutes": 10.0,
        "top_blockers": [
            "replace_with_real_external_feedback"
        ],
        "channels": ["discord"],
        "notes": "Template file. Replace with real cohort evidence.",
    }


def _merge_registry(
    *,
    registry_path: Path,
    release_window: str,
    beginner: dict[str, Any],
    professional: dict[str, Any],
    summary_path: Path,
) -> dict[str, Any]:
    payload = _load_json(registry_path)
    if not isinstance(payload, dict):
        raise ValueError(f"registry must be JSON object: {registry_path}")
    cohorts = payload.get("cohorts", [])
    if not isinstance(cohorts, list):
        raise ValueError("registry `cohorts` must be an array")

    beginner_count = int(beginner.get("participant_count", 0))
    pro_count = int(professional.get("participant_count", 0))
    status = "completed" if beginner_count > 0 and pro_count > 0 else "planned"
    channels = sorted(set(list(beginner.get("channels", [])) + list(professional.get("channels", []))))
    notes = []
    if beginner.get("top_blockers"):
        notes.append(f"beginner blockers: {', '.join(beginner['top_blockers'][:3])}")
    if professional.get("top_blockers"):
        notes.append(f"professional blockers: {', '.join(professional['top_blockers'][:3])}")

    updated_row = {
        "release_window": release_window,
        "status": status,
        "external_beginner_participants": beginner_count,
        "external_pro_participants": pro_count,
        "internal_proxy_participants": int(
            max(
                0,
                int(next((row.get("internal_proxy_participants", 0) for row in cohorts if row.get("release_window") == release_window), 0)),
            )
        ),
        "channels": channels or ["discord"],
        "owner": "research-ops",
        "artifacts": {
            "summary": str(summary_path),
        },
        "next_actions": [
            "Review blockers and convert to prioritized TODO items",
            "Re-run cohort for next release window with updated onboarding flow",
        ],
    }
    replaced = False
    new_rows: list[dict[str, Any]] = []
    for row in cohorts:
        if not isinstance(row, dict):
            continue
        if str(row.get("release_window", "")).strip() == release_window:
            new_rows.append(updated_row)
            replaced = True
        else:
            new_rows.append(row)
    if not replaced:
        new_rows.append(updated_row)

    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    payload["cohorts"] = sorted(new_rows, key=lambda row: str(row.get("release_window", "")))
    return payload


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default="data/validation/external_beta/cohort_registry.json")
    parser.add_argument("--user-research", default="docs/USER_RESEARCH_2026_03.md")
    parser.add_argument("--release-window", default="")
    parser.add_argument("--beginner-report", default="")
    parser.add_argument("--professional-report", default="")
    parser.add_argument("--summary-out", default="")
    parser.add_argument("--write-templates", action="store_true")
    parser.add_argument("--update-registry", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    registry_path = Path(args.registry)
    user_research_path = Path(args.user_research)
    release_window = str(args.release_window).strip() or _extract_release_window(user_research_path)

    reports_root = Path("data/validation/external_beta/reports")
    beginner_report_path = Path(args.beginner_report) if str(args.beginner_report).strip() else reports_root / f"{release_window}_beginner.json"
    professional_report_path = Path(args.professional_report) if str(args.professional_report).strip() else reports_root / f"{release_window}_professional.json"
    summary_out = Path(args.summary_out) if str(args.summary_out).strip() else reports_root / f"{release_window}_summary.json"

    if args.write_templates:
        if not beginner_report_path.exists():
            _write_json(beginner_report_path, _default_report("beginner"))
        if not professional_report_path.exists():
            _write_json(professional_report_path, _default_report("professional"))

    if not beginner_report_path.exists() or not professional_report_path.exists():
        raise SystemExit(
            f"Missing cohort reports. Create files first or run with --write-templates. "
            f"beginner={beginner_report_path} professional={professional_report_path}"
        )

    beginner_raw = _load_json(beginner_report_path)
    professional_raw = _load_json(professional_report_path)
    errors: list[str] = []
    beginner_errors, beginner = _validate_report(beginner_raw, expected_persona="beginner", path=beginner_report_path)
    professional_errors, professional = _validate_report(
        professional_raw,
        expected_persona="professional",
        path=professional_report_path,
    )
    errors.extend(beginner_errors)
    errors.extend(professional_errors)
    if errors:
        for item in errors:
            print(f"FAIL {item}")
        return 2

    summary = {
        "schema_version": "1",
        "release_window": release_window,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cohorts": {
            "beginner": beginner,
            "professional": professional,
        },
        "metrics": {
            "external_beginner_participants": int(beginner["participant_count"]),
            "external_pro_participants": int(professional["participant_count"]),
            "median_time_to_first_meaningful_result_minutes": {
                "beginner": float(beginner["median_time_to_first_meaningful_result_minutes"]),
                "professional": float(professional["median_time_to_first_meaningful_result_minutes"]),
            },
            "task_completion_rate": {
                "beginner": float(beginner["task_completion_rate"]),
                "professional": float(professional["task_completion_rate"]),
            },
        },
        "top_blockers": {
            "beginner": list(beginner["top_blockers"])[:5],
            "professional": list(professional["top_blockers"])[:5],
        },
    }

    if not args.dry_run:
        _write_json(summary_out, summary)

    if args.update_registry:
        updated_registry = _merge_registry(
            registry_path=registry_path,
            release_window=release_window,
            beginner=beginner,
            professional=professional,
            summary_path=summary_out,
        )
        if not args.dry_run:
            _write_json(registry_path, updated_registry)

    print(
        json.dumps(
            {
                "validated": True,
                "release_window": release_window,
                "beginner_report": str(beginner_report_path),
                "professional_report": str(professional_report_path),
                "summary_out": str(summary_out),
                "registry_updated": bool(args.update_registry and not args.dry_run),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
