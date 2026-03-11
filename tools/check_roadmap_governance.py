#!/usr/bin/env python3
"""Validate roadmap parity/moat governance and review freshness (MOAT-15)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path

TRACK_RE = re.compile(r"Track:\s*`?(parity|moat)`?", re.I)
TYPE_RE = re.compile(r"Type:\s*`?(engineering|human_only)`?", re.I)
CHECKBOX_RE = re.compile(r"^- \[(?P<done>[xX ])\]\s+.*$", re.M)
LAST_UPDATED_RE = re.compile(r"Last updated:\s*(\d{4}-\d{2}-\d{2})")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--todo", default="docs/TODO.md")
    parser.add_argument("--policy", default="config/moat/roadmap_governance.json")
    parser.add_argument("--today", default="")
    return parser


def _parse_items(todo_text: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in todo_text.splitlines():
        token = line.strip()
        if not token.startswith("- ["):
            continue
        cb = CHECKBOX_RE.match(token)
        if cb is None:
            continue
        track_match = TRACK_RE.search(token)
        type_match = TYPE_RE.search(token)
        track = track_match.group(1).lower() if track_match else ""
        row_type = type_match.group(1).lower() if type_match else "engineering"
        rows.append(
            {
                "line": token,
                "done": cb.group("done").lower() == "x",
                "track": track,
                "type": row_type,
            }
        )
    return rows


def _parity_p0_state(todo_text: str) -> tuple[bool, bool]:
    """Return (found, complete) for the Parity P0 subsection in TODO."""
    in_p0 = False
    found = False
    has_open = False
    for line in todo_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("### "):
            if in_p0:
                break
            if stripped.lower().startswith("### p0 "):
                in_p0 = True
                found = True
            continue
        if not in_p0:
            continue
        if stripped.startswith("- [ ]"):
            has_open = True
    return found, not has_open


def _parse_review_date(path: Path) -> date | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    match = LAST_UPDATED_RE.search(text)
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y-%m-%d").date()


def main() -> int:
    args = build_arg_parser().parse_args()
    todo_path = Path(args.todo)
    policy = json.loads(Path(args.policy).read_text(encoding="utf-8"))

    min_moat_share = float(policy.get("min_moat_share_after_parity_p0", 0.60))
    quarterly = policy.get("quarterly_review", {})
    review_file = Path(str(quarterly.get("review_file", "docs/MOAT_QUARTERLY_REVIEW.md")))
    max_age_days = int(quarterly.get("max_review_age_days", 100))

    todo_text = todo_path.read_text(encoding="utf-8")
    rows = _parse_items(todo_text)

    open_rows = [
        row
        for row in rows
        if not bool(row["done"])
        and row["track"] in {"parity", "moat"}
        and row.get("type") != "human_only"
    ]
    moat_open = sum(1 for row in open_rows if row["track"] == "moat")
    parity_open = sum(1 for row in open_rows if row["track"] == "parity")
    total_open = len(open_rows)
    moat_share = (float(moat_open) / float(total_open)) if total_open > 0 else 1.0
    p0_found, p0_complete = _parity_p0_state(todo_text)

    today = (
        datetime.strptime(str(args.today), "%Y-%m-%d").date()
        if str(args.today).strip()
        else date.today()
    )
    review_date = _parse_review_date(review_file)
    review_age_days = (today - review_date).days if review_date is not None else None

    reasons: list[str] = []
    enforce_moat_share = (not p0_found) or p0_complete
    if enforce_moat_share and moat_share < min_moat_share:
        reasons.append("moat_share_below_policy")
    if review_date is None:
        reasons.append("quarterly_review_missing_or_unparseable")
    elif int(review_age_days or 0) > max_age_days:
        reasons.append("quarterly_review_stale")

    payload = {
        "passed": not reasons,
        "open_items": {
            "total": total_open,
            "moat": moat_open,
            "parity": parity_open,
            "moat_share": moat_share,
            "min_moat_share": min_moat_share,
            "parity_p0_found": p0_found,
            "parity_p0_complete": p0_complete,
            "moat_share_enforced": enforce_moat_share,
        },
        "quarterly_review": {
            "path": str(review_file),
            "last_updated": review_date.isoformat() if review_date else None,
            "age_days": review_age_days,
            "max_age_days": max_age_days,
        },
        "reasons": reasons,
    }
    print(json.dumps(payload, sort_keys=True))
    return 0 if payload["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
