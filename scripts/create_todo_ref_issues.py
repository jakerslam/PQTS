#!/usr/bin/env python3
"""Create GitHub issues from open TODO entries that carry SRS Ref IDs."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

REF_RE = re.compile(r"Ref:\s*([^`]+)")


def _run(cmd: list[str]) -> str:
    completed = subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa: S603
    return completed.stdout


def parse_open_todo_items(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        token = line.strip()
        if not token.startswith("- [ ]"):
            continue
        ref_match = REF_RE.search(token)
        if not ref_match:
            continue
        text = token[len("- [ ] ") :]
        if " (`ROI" in text:
            text = text.split(" (`ROI", 1)[0].strip()
        rows.append(
            {
                "text": text,
                "refs": ref_match.group(1).strip(),
                "raw": token,
            }
        )
    return rows


def existing_titles(repo: str) -> set[str]:
    payload = _run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "all",
            "--limit",
            "1000",
            "--json",
            "title",
        ]
    )
    rows = json.loads(payload)
    return {str(row.get("title", "")).strip() for row in rows if isinstance(row, dict)}


def normalize_refs(refs: str) -> str:
    tokens = [token.strip() for token in refs.split(",") if token.strip()]
    return ", ".join(tokens)


def build_issue_title(item: dict[str, str]) -> str:
    refs = normalize_refs(item["refs"])
    text = item["text"]
    return f"{refs}: {text}"


def create_issue(repo: str, title: str, body: str) -> None:
    _run(
        [
            "gh",
            "issue",
            "create",
            "--repo",
            repo,
            "--title",
            title,
            "--label",
            "enhancement",
            "--body",
            body,
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="jakerslam/PQTS")
    parser.add_argument("--todo", default="docs/TODO.md")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    todo_path = Path(args.todo)
    if not todo_path.exists():
        raise SystemExit(f"todo file not found: {todo_path}")

    items = parse_open_todo_items(todo_path)
    existing = existing_titles(args.repo)

    created = 0
    skipped = 0
    for idx, item in enumerate(items, start=1):
        if int(args.limit) > 0 and idx > int(args.limit):
            break
        title = build_issue_title(item)
        if title in existing:
            print(f"SKIP {title}")
            skipped += 1
            continue

        body = (
            "Source: docs/TODO.md\n\n"
            f"TODO line:\n- {item['raw']}\n\n"
            "Acceptance:\n"
            "- Implement requirement(s) referenced in Ref IDs.\n"
            "- Add/adjust tests for behavior and contracts.\n"
            "- Update docs/TODO.md checkbox and close issue when merged.\n"
        )
        if args.execute:
            create_issue(args.repo, title, body)
            print(f"CREATED {title}")
            existing.add(title)
            created += 1
        else:
            print(f"DRY-RUN {title}")

    print(f"Summary: created={created} skipped={skipped} parsed={len(items)} execute={bool(args.execute)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
