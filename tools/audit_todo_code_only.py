#!/usr/bin/env python3
"""Strict code-only TODO audit: require concrete code + verification evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CHECK_RE = re.compile(r"^(\s*)- \[([xX ])\] (.*)$")
EVIDENCE_RE = re.compile(r"Evidence:\s*([^`]+)")
TYPE_RE = re.compile(r"Type:\s*([a-z_]+)", re.IGNORECASE)
REF_RE = re.compile(r"Ref:\s*([^`]+)")

CODE_EXTENSIONS = {
    ".py",
    ".rs",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".java",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".sql",
    ".sh",
}

CODE_PREFIXES = (
    "src/",
    "apps/",
    "services/",
    "scripts/",
    "tools/",
    "native/",
    ".github/workflows/",
)

NON_CODE_PREFIXES = (
    "docs/",
    "data/",
    "results/",
    "research/",
    "config/",
)

TEST_COMMAND_HINTS = (
    "pytest",
    "make test",
    "make lint",
    "make dod-audit",
    "make codex-enforcer",
    "make assimilation-66-71-check",
    "make unmapped-srs-check",
    "make governance-check",
    "ruff",
    "mypy",
    "flake8",
    "check_",
)


def _normalize(token: str) -> str:
    text = token.strip().strip("`")
    if text.startswith("./"):
        text = text[2:]
    return text


def _extract_evidence_tokens(body: str) -> list[str]:
    match = EVIDENCE_RE.search(body)
    if not match:
        return []
    raw = match.group(1)
    return [item.strip() for item in raw.split(";") if item.strip()]


def _is_probable_command(token: str) -> bool:
    if " " in token:
        return True
    if token.startswith("make"):
        return True
    if token in {"pytest", "ruff", "mypy", "flake8"}:
        return True
    return False


def _is_code_file_path(token: str, repo_root: Path) -> bool:
    normalized = _normalize(token)
    if not normalized:
        return False
    if normalized in {"Makefile", "pyproject.toml", "main.py"}:
        return True
    if any(normalized.startswith(prefix) for prefix in NON_CODE_PREFIXES):
        return False
    if normalized.startswith("tests/"):
        return False
    if any(normalized.startswith(prefix) for prefix in CODE_PREFIXES):
        return Path(repo_root / normalized).exists()
    if Path(normalized).suffix in CODE_EXTENSIONS and "/" in normalized:
        return Path(repo_root / normalized).exists()
    return False


def _is_test_evidence(token: str, repo_root: Path) -> bool:
    normalized = _normalize(token).lower()
    if not normalized:
        return False
    if _is_probable_command(normalized):
        return any(hint in normalized for hint in TEST_COMMAND_HINTS)
    if normalized.startswith("tests/"):
        return Path(repo_root / normalized).exists()
    if normalized.startswith("tools/check_") and normalized.endswith(".py"):
        return Path(repo_root / normalized).exists()
    if normalized.startswith("scripts/run_") and normalized.endswith(".py"):
        return "check" in normalized or "benchmark" in normalized
    return False


def _item_type(body: str) -> str:
    match = TYPE_RE.search(body)
    if not match:
        return "unknown"
    return match.group(1).lower()


def audit_todo_code_only(todo_path: Path, repo_root: Path) -> dict[str, int]:
    lines = todo_path.read_text(encoding="utf-8").splitlines()
    out_lines: list[str] = []
    checked_before = 0
    checked_after = 0
    considered = 0
    unmarked_missing_code = 0
    unmarked_missing_test = 0
    excluded_human_only = 0
    excluded_not_ref = 0

    for line in lines:
        match = CHECK_RE.match(line)
        if not match:
            out_lines.append(line)
            continue
        indent, mark, body = match.groups()
        checked = mark.lower() == "x"
        if checked:
            checked_before += 1

        if not REF_RE.search(body):
            excluded_not_ref += 1
            out_lines.append(line)
            if checked:
                checked_after += 1
            continue

        if _item_type(body) == "human_only":
            excluded_human_only += 1
            out_lines.append(line)
            if checked:
                checked_after += 1
            continue

        considered += 1
        evidence_tokens = _extract_evidence_tokens(body)
        has_code = any(_is_code_file_path(token, repo_root=repo_root) for token in evidence_tokens)
        has_test = any(_is_test_evidence(token, repo_root=repo_root) for token in evidence_tokens)

        if checked and not has_code:
            checked = False
            unmarked_missing_code += 1
        if checked and not has_test:
            checked = False
            unmarked_missing_test += 1

        out_lines.append(f"{indent}- [{'x' if checked else ' '}] {body}")
        if checked:
            checked_after += 1

    todo_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return {
        "checked_before": checked_before,
        "checked_after": checked_after,
        "considered_ref_engineering_items": considered,
        "excluded_human_only_ref_items": excluded_human_only,
        "excluded_non_ref_items": excluded_not_ref,
        "unmarked_missing_code_evidence": unmarked_missing_code,
        "unmarked_missing_test_evidence": unmarked_missing_test,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--todo", default="docs/TODO.md")
    parser.add_argument("--repo-root", default=".")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    stats = audit_todo_code_only(Path(args.todo), repo_root=Path(args.repo_root))
    print(json.dumps(stats, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
