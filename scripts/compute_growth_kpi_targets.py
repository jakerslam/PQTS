#!/usr/bin/env python3
"""Compute growth KPI digest and roadmap reprioritization signal."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

_DOC_START = "<!-- GROWTH_KPI_DIGEST:START -->"
_DOC_END = "<!-- GROWTH_KPI_DIGEST:END -->"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"history payload must be object: {path}")
    return payload


def _metric_missed(row: dict[str, Any], metric: str) -> bool:
    token = row.get(metric)
    if not isinstance(token, dict):
        return False
    try:
        actual = float(token.get("actual", 0.0))
        target = float(token.get("target", 0.0))
    except (TypeError, ValueError):
        return False
    return actual < target


def _build_digest(history: dict[str, Any]) -> dict[str, Any]:
    rows = history.get("months", [])
    if not isinstance(rows, list):
        raise ValueError("history.months must be an array")
    months: list[dict[str, Any]] = [row for row in rows if isinstance(row, dict)]
    months = sorted(months, key=lambda row: str(row.get("month", "")))
    metrics = ["stars", "forks", "docs_engagement", "onboarding_conversion_pct"]
    consecutive_miss_windows = 0
    max_consecutive_miss_windows = 0
    last_month = ""
    latest_targets: dict[str, Any] = {}
    for row in months:
        month = str(row.get("month", "")).strip()
        if month:
            last_month = month
        missed = any(_metric_missed(row, metric) for metric in metrics)
        if missed:
            consecutive_miss_windows += 1
        else:
            consecutive_miss_windows = 0
        max_consecutive_miss_windows = max(max_consecutive_miss_windows, consecutive_miss_windows)
        latest_targets = row

    reprioritize = max_consecutive_miss_windows >= 2
    actions = []
    if reprioritize:
        actions.append("Prioritize onboarding/usability conversion work over new feature expansion for next sprint.")
        actions.append("Require roadmap review memo linked to latest KPI digest before closing growth-related TODO items.")
    else:
        actions.append("Maintain current roadmap split while monitoring monthly KPI trend.")

    return {
        "schema_version": "1",
        "windows_evaluated": len(months),
        "latest_month": last_month,
        "max_consecutive_miss_windows": max_consecutive_miss_windows,
        "roadmap_reprioritization_required": reprioritize,
        "recommended_actions": actions,
        "latest_metrics": latest_targets,
    }


def _render_digest_md(digest: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("## Automated KPI Digest")
    lines.append("")
    lines.append(f"- `latest_month`: {digest.get('latest_month', '')}")
    lines.append(f"- `windows_evaluated`: {digest.get('windows_evaluated', 0)}")
    lines.append(
        "- `max_consecutive_miss_windows`: "
        f"{digest.get('max_consecutive_miss_windows', 0)}"
    )
    lines.append(
        "- `roadmap_reprioritization_required`: "
        f"{str(bool(digest.get('roadmap_reprioritization_required', False))).lower()}"
    )
    lines.append("")
    lines.append("### Recommended Actions")
    lines.append("")
    for action in list(digest.get("recommended_actions", [])):
        lines.append(f"- {action}")
    lines.append("")
    return "\n".join(lines)


def _upsert_digest_section(review_doc: Path, digest_md: str) -> str:
    text = review_doc.read_text(encoding="utf-8")
    block = f"{_DOC_START}\n{digest_md}\n{_DOC_END}"
    if _DOC_START in text and _DOC_END in text:
        start = text.index(_DOC_START)
        end = text.index(_DOC_END) + len(_DOC_END)
        return text[:start] + block + text[end:]
    if not text.endswith("\n"):
        text += "\n"
    return text + "\n" + block + "\n"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", default="config/growth/community_kpi_history.json")
    parser.add_argument("--review-doc", default="docs/GROWTH_KPI_REVIEW.md")
    parser.add_argument("--out-json", default="docs/GROWTH_KPI_DIGEST.json")
    parser.add_argument("--check", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    history_path = Path(args.history)
    review_doc_path = Path(args.review_doc)
    out_json_path = Path(args.out_json)

    history = _load_json(history_path)
    digest = _build_digest(history)
    digest_md = _render_digest_md(digest)
    updated_review = _upsert_digest_section(review_doc_path, digest_md)
    digest_json = json.dumps(digest, indent=2, sort_keys=True) + "\n"

    if args.check:
        current_doc = review_doc_path.read_text(encoding="utf-8")
        current_json = out_json_path.read_text(encoding="utf-8") if out_json_path.exists() else ""
        ok = current_doc == updated_review and current_json == digest_json
        if not ok:
            print("FAIL growth KPI digest out of date; run scripts/compute_growth_kpi_targets.py")
            return 2
    else:
        review_doc_path.write_text(updated_review, encoding="utf-8")
        out_json_path.write_text(digest_json, encoding="utf-8")

    print(
        json.dumps(
            {
                "validated": True,
                "history": str(history_path),
                "review_doc": str(review_doc_path),
                "out_json": str(out_json_path),
                "roadmap_reprioritization_required": bool(
                    digest.get("roadmap_reprioritization_required", False)
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
