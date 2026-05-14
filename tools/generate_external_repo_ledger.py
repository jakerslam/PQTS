#!/usr/bin/env python3
"""Generate an assimilation ledger for a cloned external repository."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List


@dataclass(frozen=True)
class LedgerRow:
    source_repo: str
    source_commit: str
    path: str
    category: str
    review_phase: str
    priority: str
    review_status: str
    assimilation_decision: str
    pqts_target: str
    license_boundary: str
    size_bytes: int
    line_count: int
    sha256: str
    notes: str


PHASE_ORDER = {
    "P0": 0,
    "P1": 1,
    "P2": 2,
    "P3": 3,
    "P4": 4,
}


def _run_git(repo: Path, args: List[str]) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def tracked_files(repo: Path) -> List[str]:
    return [line for line in _run_git(repo, ["ls-files"]).splitlines() if line.strip()]


def source_commit(repo: Path) -> str:
    return _run_git(repo, ["rev-parse", "--short=12", "HEAD"])


def source_origin(repo: Path) -> str:
    return _run_git(repo, ["config", "--get", "remote.origin.url"])


def classify_path(path: str) -> tuple[str, str, str, str, str]:
    """Return category, phase, priority, target, and notes for an external file."""
    p = path.lower()

    if p in {"readme.md", "license", "contributing.md", "pyproject.toml"} or p.startswith(
        ("requirements", "config_examples/")
    ):
        return (
            "repo_metadata",
            "P0",
            "high",
            "docs/assimilation + dependency policy",
            "Start here to understand scope, license, install surface, and config idioms.",
        )

    if p.startswith("freqtrade/strategy/") or p.startswith("freqtrade/templates/") or p.startswith(
        "docs/strategy"
    ):
        return (
            "strategy_interface",
            "P0",
            "high",
            "src/research/strategy_studio.py + src/research/ai_agent.py",
            "Study strategy API contracts and parameter ergonomics; reimplement ideas PQTS-native.",
        )

    if p.startswith("freqtrade/optimize/") or "backtest" in p or "lookahead" in p or "recursive" in p:
        return (
            "backtesting_validation",
            "P0",
            "high",
            "src/research + scripts/run_real_money_validation.py",
            "Study validation, reporting, lookahead, and optimization workflow patterns.",
        )

    if p.startswith("freqtrade/plugins/protections/") or p.startswith(
        ("freqtrade/wallets.py", "freqtrade/leverage/", "docs/stoploss", "docs/leverage")
    ):
        return (
            "risk_protection",
            "P0",
            "high",
            "src/risk + src/execution/risk_aware_router.py",
            "Map concepts only; PQTS router and kill-switches remain non-bypassable.",
        )

    if p.startswith("freqtrade/freqai/") or "freqai" in p or "hyperopt" in p:
        return (
            "hyperopt_ml",
            "P1",
            "high",
            "src/research/advanced_training.py + src/research/hyperopt.py",
            "Study ML/training orchestration and optimization surfaces.",
        )

    if p.startswith("freqtrade/exchange/") or p.startswith(
        ("freqtrade/data/history/", "freqtrade/data/converter/", "docs/data-download", "docs/exchanges")
    ):
        return (
            "market_data_exchange",
            "P1",
            "medium",
            "src/markets + src/adapters + data/lake",
            "Assimilate data/exchange abstraction ideas in read-only/shadow mode first.",
        )

    if p.startswith(("freqtrade/rpc/", "freqtrade/commands/", "docs/telegram", "docs/rest-api", "docs/freq-ui")):
        return (
            "ops_control_surface",
            "P2",
            "medium",
            "services/api + apps/web + scripts ops commands",
            "Study control-plane UX and command surfaces; preserve PQTS approval gates.",
        )

    if p.startswith(("freqtrade/persistence/", "freqtrade/data/btanalysis/")):
        return (
            "persistence_analysis",
            "P2",
            "medium",
            "src/analytics + src/execution/order_ledger.py",
            "Study analysis persistence, not execution-ledger replacement.",
        )

    if p.startswith("tests/"):
        return (
            "test_suite",
            "P2",
            "medium",
            "tests",
            "Use as behavioral coverage inspiration, not as copied fixtures.",
        )

    if p.startswith(("docs/", "mkdocs.yml", ".readthedocs.yml")):
        return (
            "documentation",
            "P3",
            "low",
            "docs",
            "Mine docs patterns and operator education only.",
        )

    if p.startswith((".github/", "docker", "build_helpers/", ".devcontainer", "setup.")):
        return (
            "build_release_ops",
            "P3",
            "low",
            ".github + docker-compose + release tooling",
            "Study project operations after core research/runtime patterns.",
        )

    return (
        "other",
        "P4",
        "low",
        "pending triage",
        "Review after higher-priority assimilation phases.",
    )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_lines(path: Path) -> int:
    try:
        payload = path.read_bytes()
    except OSError:
        return 0
    if not payload:
        return 0
    return payload.count(b"\n") + (0 if payload.endswith(b"\n") else 1)


def build_rows(repo: Path, repo_name: str) -> List[LedgerRow]:
    commit = source_commit(repo)
    rows: List[LedgerRow] = []
    for rel_path in tracked_files(repo):
        abs_path = repo / rel_path
        category, phase, priority, target, notes = classify_path(rel_path)
        rows.append(
            LedgerRow(
                source_repo=repo_name,
                source_commit=commit,
                path=rel_path,
                category=category,
                review_phase=phase,
                priority=priority,
                review_status="unreviewed",
                assimilation_decision="pending",
                pqts_target=target,
                license_boundary="GPL-3.0 study-only: do not copy source into PQTS without explicit license decision.",
                size_bytes=abs_path.stat().st_size if abs_path.exists() else 0,
                line_count=count_lines(abs_path) if abs_path.exists() else 0,
                sha256=file_sha256(abs_path) if abs_path.exists() else "",
                notes=notes,
            )
        )

    return sorted(
        rows,
        key=lambda row: (
            PHASE_ORDER.get(row.review_phase, 99),
            0 if row.priority == "high" else 1 if row.priority == "medium" else 2,
            row.category,
            row.path,
        ),
    )


def write_csv(path: Path, rows: Iterable[LedgerRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows_list = list(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows_list[0]).keys()))
        writer.writeheader()
        for row in rows_list:
            writer.writerow(asdict(row))


def write_json(path: Path, *, rows: List[LedgerRow], metadata: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"metadata": metadata, "files": [asdict(row) for row in rows]}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, *, rows: List[LedgerRow], metadata: dict, csv_path: Path, json_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    category_counts = Counter(row.category for row in rows)
    phase_counts = Counter(row.review_phase for row in rows)
    high_rows = [row for row in rows if row.priority == "high"][:80]

    lines = [
        "# Freqtrade Assimilation Ledger",
        "",
        "This is a work ledger for studying the cloned Freqtrade repository without importing its execution path into PQTS.",
        "",
        "## Source Snapshot",
        "",
        f"- Source repo: `{metadata['source_repo']}`",
        f"- Source origin: `{metadata['source_origin']}`",
        f"- Source commit: `{metadata['source_commit']}`",
        f"- Generated at: `{metadata['generated_at']}`",
        f"- Tracked files: `{metadata['file_count']}`",
        f"- CSV ledger: [{csv_path.name}]({csv_path.name})",
        f"- JSON ledger: [{json_path.name}]({json_path.name})",
        "",
        "## Safety Boundary",
        "",
        "- Treat Freqtrade as GPL-3.0 study material unless a deliberate license decision says otherwise.",
        "- Do not copy Freqtrade source into PQTS.",
        "- Assimilate behavior as PQTS-native designs, tests, contracts, and docs.",
        "- External code must never submit orders or bypass `execution.RiskAwareRouter.submit_order()`.",
        "- Any assimilated feature must pass PQTS OOS, walk-forward, deflated-Sharpe, cost, promotion, and kill-switch gates.",
        "",
        "## Review Phases",
        "",
        "| Phase | Meaning | Files |",
        "| --- | --- | ---: |",
    ]
    phase_labels = {
        "P0": "Immediate assimilation candidates: strategy API, backtesting, protection, repo metadata",
        "P1": "High-value research/data patterns: hyperopt, FreqAI, exchange/data ingestion",
        "P2": "Control surfaces, persistence, and behavior-rich test coverage",
        "P3": "Documentation, build, release, and operator ergonomics",
        "P4": "Remaining triage",
    }
    for phase in sorted(phase_counts, key=lambda key: PHASE_ORDER.get(key, 99)):
        lines.append(f"| `{phase}` | {phase_labels.get(phase, 'Triage')} | {phase_counts[phase]} |")

    lines.extend(["", "## Category Counts", "", "| Category | Files |", "| --- | ---: |"])
    for category, count in sorted(category_counts.items()):
        lines.append(f"| `{category}` | {count} |")

    lines.extend(
        [
            "",
            "## High-Priority File Queue",
            "",
            "Use the CSV/JSON ledgers for the exhaustive list. This queue shows the first high-priority files to work through.",
            "",
            "| Phase | Category | File | PQTS target | Status |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in high_rows:
        lines.append(
            f"| `{row.review_phase}` | `{row.category}` | `{row.path}` | `{row.pqts_target}` | `{row.review_status}` |"
        )

    lines.extend(
        [
            "",
            "## Ledger Columns",
            "",
            "- `review_status`: `unreviewed`, `reading`, `mapped`, `implemented`, `rejected`, or `blocked`.",
            "- `assimilation_decision`: `pending`, `study_only`, `pqts_native_candidate`, `implemented`, `rejected_license`, or `not_relevant`.",
            "- `pqts_target`: the PQTS area likely to receive any native implementation.",
            "- `license_boundary`: default legal/safety boundary for the file.",
            "",
            "## Suggested Workflow",
            "",
            "1. Start with `P0` rows in the CSV.",
            "2. Read the external file and write a short finding in `notes` or a follow-up assimilation memo.",
            "3. Decide `study_only`, `pqts_native_candidate`, or `not_relevant`.",
            "4. Implement only PQTS-native behavior with new tests and promotion gates.",
            "5. Preserve router-only execution and never instantiate external adapters in live paths.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="external_repos/freqtrade")
    parser.add_argument("--repo-name", default="freqtrade/freqtrade")
    parser.add_argument("--out-dir", default="docs/assimilation")
    parser.add_argument("--basename", default="freqtrade_file_ledger")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo = Path(args.repo)
    if not (repo / ".git").exists():
        raise FileNotFoundError(f"Expected cloned git repository at {repo}")

    rows = build_rows(repo=repo, repo_name=str(args.repo_name))
    if not rows:
        raise RuntimeError(f"No tracked files found in {repo}")

    out_dir = Path(args.out_dir)
    csv_path = out_dir / f"{args.basename}.csv"
    json_path = out_dir / f"{args.basename}.json"
    md_path = out_dir / "FREQTRADE_ASSIMILATION_LEDGER.md"
    metadata = {
        "source_repo": str(args.repo_name),
        "source_origin": source_origin(repo),
        "source_commit": source_commit(repo),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(rows),
        "generator": "tools/generate_external_repo_ledger.py",
    }

    write_csv(csv_path, rows)
    write_json(json_path, rows=rows, metadata=metadata)
    write_markdown(md_path, rows=rows, metadata=metadata, csv_path=csv_path, json_path=json_path)
    print(json.dumps({"csv": str(csv_path), "json": str(json_path), "markdown": str(md_path), **metadata}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
