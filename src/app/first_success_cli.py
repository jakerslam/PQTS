"""First-success CLI commands for quick onboarding flows."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import platform
import shutil
import subprocess
import sys
from contextlib import redirect_stdout
from datetime import datetime, timezone
from difflib import unified_diff
from pathlib import Path
from typing import Sequence

from analytics.notifications import NotificationChannels, NotificationDispatcher
from app.operator_experience import (
    explain_block_reason,
    explain_strategy,
    latest_paths,
    list_risk_profiles,
    list_strategy_catalog,
    recommend_risk_profile,
)
from strategies.plugin_sdk import scaffold_strategy_plugin

REPO_ROOT = Path(__file__).resolve().parents[2]
FIRST_SUCCESS_COMMANDS = {
    "init",
    "demo",
    "backtest",
    "paper",
    "skills",
    "doctor",
    "quickstart",
    "strategies",
    "risk",
    "status",
    "notify",
    "explain",
    "artifacts",
    "new-strategy",
}

BACKTEST_TEMPLATE_STRATEGY_MAP = {
    "momentum": "trend_following",
    "trend": "trend_following",
    "mean_reversion": "mean_reversion",
    "mean-reversion": "mean_reversion",
    "market_making": "market_making",
    "market-making": "market_making",
    "funding_arb": "funding_arbitrage",
    "funding-arb": "funding_arbitrage",
}


def _default_repo_base_url() -> str:
    env_value = str(os.getenv("PQTS_REPO_HTTP_URL", "")).strip()
    if env_value:
        return env_value.rstrip("/")
    fallback = "https://raw.githubusercontent.com/jakerslam/PQTS/main"
    try:
        remote = (
            subprocess.check_output(  # noqa: S603
                ["git", "config", "--get", "remote.origin.url"],
                cwd=str(REPO_ROOT),
                text=True,
                stderr=subprocess.DEVNULL,
            )
            .strip()
            .rstrip("/")
        )
    except Exception:
        return fallback

    owner_repo = ""
    if remote.startswith("https://github.com/"):
        owner_repo = remote.removeprefix("https://github.com/").removesuffix(".git")
    elif remote.startswith("git@github.com:"):
        owner_repo = remote.removeprefix("git@github.com:").removesuffix(".git")
    if "/" not in owner_repo:
        return fallback
    return f"https://raw.githubusercontent.com/{owner_repo}/main"


def _discover_skill_files(skills_dir: Path) -> list[Path]:
    if not skills_dir.exists():
        return []
    return sorted(path for path in skills_dir.glob("*/SKILL.md") if path.is_file())


def _skill_title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        token = line.strip()
        if token.startswith("#"):
            return token.lstrip("#").strip() or path.parent.name
    return path.parent.name


def _skill_relative_path(path: Path, *, skills_dir: Path) -> Path:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve())
    except Exception:
        try:
            return path.resolve().relative_to(skills_dir.resolve().parent)
        except Exception:
            return Path(path.name)


def _run_skills_list(args: argparse.Namespace) -> int:
    skills_dir = Path(args.skills_dir).expanduser().resolve()
    files = _discover_skill_files(skills_dir)
    if not files:
        print(f"No skills found in: {skills_dir}")
        return 0
    print(f"Discovered {len(files)} skills in {skills_dir}:")
    for path in files:
        rel = _skill_relative_path(path, skills_dir=skills_dir)
        print(f"  - {path.parent.name}: {_skill_title(path)} ({rel.as_posix()})")
    return 0


def _run_skills_urls(args: argparse.Namespace) -> int:
    skills_dir = Path(args.skills_dir).expanduser().resolve()
    repo_base_url = str(args.repo_base_url).strip().rstrip("/")
    files = _discover_skill_files(skills_dir)
    if not files:
        print(f"No skills found in: {skills_dir}")
        return 0
    print(f"Skill raw URLs ({len(files)}):")
    for path in files:
        rel = _skill_relative_path(path, skills_dir=skills_dir)
        print(f"  {repo_base_url}/{rel.as_posix()}")
    return 0


def should_use_first_success_cli(argv: Sequence[str]) -> bool:
    """Route to first-success CLI for explicit onboarding commands and help."""
    args = [str(token).strip() for token in argv]
    if not args:
        return True
    lead = args[0]
    if lead in {"-h", "--help", "help"}:
        return True
    return lead in FIRST_SUCCESS_COMMANDS


def _run_command(command: list[str], *, cwd: Path | None = None) -> int:
    completed = subprocess.run(command, cwd=str(cwd) if cwd else None, check=False)  # noqa: S603
    return int(completed.returncode)


def _python() -> str:
    return str(Path(sys.executable))


def _print_next_steps(steps: Sequence[str]) -> None:
    if not steps:
        return
    print("\nNext steps:")
    for step in steps:
        print(f"  {step}")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _config_fingerprint(path: Path) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def _find_previous_template_artifact(out_dir: Path, *, current_path: Path) -> Path | None:
    candidates = sorted(out_dir.glob("template_run_*.json"))
    previous = [path for path in candidates if path != current_path]
    return previous[-1] if previous else None


def _write_template_run_artifacts(
    *,
    out_dir: Path,
    mode: str,
    template_name: str,
    strategy: str,
    config_path: Path,
    command: list[str],
    extra: dict[str, object] | None = None,
) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _utc_stamp()
    artifact_path = out_dir / f"template_run_{stamp}.json"
    payload: dict[str, object] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": str(mode),
        "template": str(template_name),
        "resolved_strategy": str(strategy),
        "config_path": str(config_path),
        "config_sha256": _config_fingerprint(config_path),
        "command": list(command),
    }
    if extra:
        payload.update(extra)
    artifact_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    diff_path = out_dir / f"template_run_diff_{stamp}.diff"
    previous_path = _find_previous_template_artifact(out_dir, current_path=artifact_path)
    if previous_path is not None:
        prev_payload = json.loads(previous_path.read_text(encoding="utf-8"))
        old = json.dumps(prev_payload, indent=2, sort_keys=True).splitlines(keepends=True)
        new = json.dumps(payload, indent=2, sort_keys=True).splitlines(keepends=True)
        diff = "".join(
            unified_diff(
                old,
                new,
                fromfile=str(previous_path.name),
                tofile=str(artifact_path.name),
            )
        )
        diff_path.write_text(diff, encoding="utf-8")
    else:
        diff_path.write_text("", encoding="utf-8")

    return {
        "template_run_artifact": str(artifact_path),
        "template_run_diff": str(diff_path),
    }


def _run_init(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    required_dirs = [
        workspace / "data" / "reports",
        workspace / "data" / "analytics",
        workspace / "data" / "tca" / "simulation",
        workspace / "results",
        workspace / "logs",
    ]
    for path in required_dirs:
        path.mkdir(parents=True, exist_ok=True)

    env_path = workspace / ".env"
    env_example = workspace / ".env.example"
    env_result = "unchanged"
    if not env_path.exists() and env_example.exists():
        shutil.copy2(env_example, env_path)
        env_result = "created_from_example"
    elif env_path.exists():
        env_result = "already_exists"
    else:
        env_result = "skipped_no_example"

    print(f"Workspace initialized at: {workspace}")
    print(f".env status: {env_result}")
    _print_next_steps(
        [
            "pqts demo",
            "pqts backtest momentum",
            "pqts paper start",
        ]
    )
    return 0


def _run_demo(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    command = [
        _python(),
        str(REPO_ROOT / "scripts" / "run_simulation_suite.py"),
        "--config",
        str(args.config),
        "--markets",
        str(args.markets),
        "--strategies",
        str(args.strategies),
        "--cycles-per-scenario",
        str(args.cycles),
        "--readiness-every",
        str(args.readiness_every),
        "--symbols-per-market",
        str(args.symbols_per_market),
        "--sleep-seconds",
        "0.0",
        "--out-dir",
        str(out_dir),
        "--telemetry-log",
        str(Path(args.telemetry_log)),
        "--tca-dir",
        str(Path(args.tca_dir)),
    ]
    if str(args.risk_profile).strip():
        command.extend(["--risk-profile", str(args.risk_profile).strip()])

    print("Running demo simulation...")
    rc = _run_command(command, cwd=REPO_ROOT)
    if rc != 0:
        return rc
    _print_next_steps(
        [
            "pqts backtest momentum",
            "pqts paper start",
            "python3 scripts/export_simulation_leaderboard_site.py --reports-dir data/reports --output-dir docs/leaderboard",
        ]
    )
    return 0


def _resolve_template_strategy(template: str) -> str:
    token = str(template).strip().lower()
    return BACKTEST_TEMPLATE_STRATEGY_MAP.get(token, token or "trend_following")


def _run_backtest(args: argparse.Namespace) -> int:
    strategy = _resolve_template_strategy(args.template)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    command = [
        _python(),
        str(REPO_ROOT / "scripts" / "run_simulation_suite.py"),
        "--config",
        str(args.config),
        "--markets",
        str(args.market),
        "--strategies",
        strategy,
        "--cycles-per-scenario",
        str(args.cycles),
        "--readiness-every",
        str(args.readiness_every),
        "--symbols-per-market",
        str(args.symbols_per_market),
        "--sleep-seconds",
        "0.0",
        "--out-dir",
        str(out_dir),
        "--telemetry-log",
        str(Path(args.telemetry_log)),
        "--tca-dir",
        str(Path(args.tca_dir)),
    ]
    if str(args.risk_profile).strip():
        command.extend(["--risk-profile", str(args.risk_profile).strip()])

    print(f"Running backtest template '{args.template}' (strategy: {strategy})...")
    rc = _run_command(command, cwd=REPO_ROOT)
    if rc != 0:
        return rc
    artifact_refs = _write_template_run_artifacts(
        out_dir=out_dir,
        mode="backtest",
        template_name=str(args.template),
        strategy=str(strategy),
        config_path=Path(args.config),
        command=command,
        extra={
            "market": str(args.market),
            "cycles": int(args.cycles),
            "risk_profile": str(args.risk_profile),
            "studio_explanation": "Template run preserves code-visible config + command artifacts.",
        },
    )
    _print_next_steps(
        [
            "Review outputs in data/reports/backtest/",
            f"Template artifact: {artifact_refs['template_run_artifact']}",
            f"Template diff: {artifact_refs['template_run_diff']}",
            "pqts paper start",
        ]
    )
    return 0


def _run_paper_start(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    command = [
        _python(),
        str(REPO_ROOT / "scripts" / "run_paper_campaign.py"),
        "--config",
        str(args.config),
        "--cycles",
        str(args.cycles),
        "--sleep-seconds",
        str(args.sleep_seconds),
        "--notional-usd",
        str(args.notional_usd),
        "--readiness-every",
        str(args.readiness_every),
        "--out-dir",
        str(out_dir),
    ]
    if str(args.symbols).strip():
        command.extend(["--symbols", str(args.symbols).strip()])
    if str(args.risk_profile).strip():
        command.extend(["--risk-profile", str(args.risk_profile).strip()])

    print("Starting paper campaign (bounded quick run)...")
    rc = _run_command(command, cwd=REPO_ROOT)
    if rc != 0:
        return rc
    artifact_refs = _write_template_run_artifacts(
        out_dir=out_dir,
        mode="paper_start",
        template_name="paper_safe",
        strategy="campaign",
        config_path=Path(args.config),
        command=command,
        extra={
            "cycles": int(args.cycles),
            "notional_usd": float(args.notional_usd),
            "risk_profile": str(args.risk_profile),
            "studio_explanation": "Paper start is one-click and paper-first; live actions remain risk-gated.",
            "why_blocked_hint": "If blocked, check readiness/kill-switch/profitability gate outputs in campaign report.",
        },
    )
    _print_next_steps(
        [
            "Inspect latest snapshot in data/reports/paper/",
            f"Template artifact: {artifact_refs['template_run_artifact']}",
            f"Template diff: {artifact_refs['template_run_diff']}",
            "python3 scripts/control_plane_report.py --events data/analytics/attribution_events.jsonl",
        ]
    )
    return 0


def _run_doctor(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    config_path = Path(args.config).expanduser()
    if not config_path.is_absolute():
        config_path = (REPO_ROOT / config_path).resolve()

    required_dirs = [
        workspace / "data" / "reports",
        workspace / "data" / "analytics",
        workspace / "data" / "tca" / "simulation",
    ]
    if bool(args.fix):
        for path in required_dirs:
            path.mkdir(parents=True, exist_ok=True)

    checks: list[dict[str, object]] = []

    py_ok = sys.version_info >= (3, 11)
    checks.append(
        {
            "name": "python_version",
            "ok": py_ok,
            "required": True,
            "detail": platform.python_version(),
        }
    )
    checks.append(
        {
            "name": "config_exists",
            "ok": config_path.exists(),
            "required": True,
            "detail": str(config_path),
        }
    )
    checks.append(
        {
            "name": "repo_layout",
            "ok": (REPO_ROOT / "src").exists() and (REPO_ROOT / "scripts").exists(),
            "required": True,
            "detail": str(REPO_ROOT),
        }
    )
    checks.append(
        {
            "name": "workspace_env",
            "ok": (workspace / ".env").exists() or (workspace / ".env.example").exists(),
            "required": False,
            "detail": str(workspace / ".env"),
        }
    )
    checks.append(
        {
            "name": "docker_available",
            "ok": shutil.which("docker") is not None,
            "required": False,
            "detail": str(shutil.which("docker") or "missing"),
        }
    )
    checks.append(
        {
            "name": "make_available",
            "ok": shutil.which("make") is not None,
            "required": False,
            "detail": str(shutil.which("make") or "missing"),
        }
    )
    checks.append(
        {
            "name": "data_dirs_ready",
            "ok": all(path.exists() for path in required_dirs),
            "required": False,
            "detail": str(workspace / "data"),
        }
    )

    print("PQTS Doctor Report")
    print("=" * 60)
    for row in checks:
        status = "PASS" if bool(row["ok"]) else "FAIL"
        req = "required" if bool(row["required"]) else "optional"
        print(f"[{status}] {row['name']} ({req}) -> {row['detail']}")

    failed_required = [row for row in checks if bool(row["required"]) and not bool(row["ok"])]
    if failed_required:
        print("\nDoctor result: failed required checks.")
        return 1
    print("\nDoctor result: environment is ready for onboarding flows.")
    return 0


def _run_quickstart(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    report_root = Path(args.report_root).expanduser().resolve()
    commands = [
        ["init", "--workspace", str(workspace)],
        ["demo", "--out-dir", str(report_root / "demo"), "--cycles", str(args.demo_cycles)],
        ["backtest", "momentum", "--out-dir", str(report_root / "backtest"), "--cycles", str(args.backtest_cycles)],
        ["paper", "start", "--out-dir", str(report_root / "paper"), "--cycles", str(args.paper_cycles)],
    ]

    print("Quickstart Plan")
    print("=" * 60)
    for index, row in enumerate(commands, start=1):
        print(f"{index}. pqts {' '.join(row)}")

    if not bool(args.execute):
        print("\nDry-run only. Re-run with --execute to run full pipeline.")
        return 0

    for row in commands:
        command = [_python(), str(REPO_ROOT / "main.py"), *row]
        rc = _run_command(command, cwd=REPO_ROOT)
        if rc != 0:
            print(f"Quickstart halted at: pqts {' '.join(row)} (exit={rc})")
            return rc
    print("\nQuickstart execution completed.")
    return 0


def _run_strategies_list(_args: argparse.Namespace) -> int:
    print("Strategy Catalog")
    print("=" * 60)
    for row in list_strategy_catalog():
        print(
            f"{row.key:20s} | {row.audience:8s} | {row.complexity:12s} | "
            f"{','.join(row.markets)}"
        )
    return 0


def _run_strategies_explain(args: argparse.Namespace) -> int:
    entry = explain_strategy(args.strategy)
    if entry is None:
        print(f"Unknown strategy: {args.strategy}")
        return 2
    print(f"{entry.label} ({entry.key})")
    print("=" * 60)
    print(f"Audience: {entry.audience}")
    print(f"Complexity: {entry.complexity}")
    print(f"Markets: {', '.join(entry.markets)}")
    print(f"Summary: {entry.summary}")
    print(f"Why it matters: {entry.why_it_matters}")
    return 0


def _run_risk_list(_args: argparse.Namespace) -> int:
    print("Risk Profiles")
    print("=" * 60)
    for row in list_risk_profiles():
        print(
            f"{row.key:14s} | audience={row.audience:8s} | max_notional={row.max_notional_pct:.2%} | "
            f"drawdown_guardrail={row.drawdown_guardrail_pct:.2%}"
        )
    return 0


def _run_risk_recommend(args: argparse.Namespace) -> int:
    profile = recommend_risk_profile(
        experience=str(args.experience),
        capital_usd=float(args.capital_usd),
        automation=str(args.automation),
    )
    print("Recommended Risk Profile")
    print("=" * 60)
    print(f"Profile: {profile.key}")
    print(f"Audience: {profile.audience}")
    print(f"Max notional: {profile.max_notional_pct:.2%}")
    print(f"Drawdown guardrail: {profile.drawdown_guardrail_pct:.2%}")
    print(f"Reason: {profile.summary}")
    return 0


def _run_status_reports(args: argparse.Namespace) -> int:
    reports_dir = Path(args.reports_dir).expanduser().resolve()
    rows = latest_paths(
        [
            "**/simulation_suite_*.json",
            "**/paper_campaign_*.json",
            "**/paper_6m_harness_*.json",
            "**/monthly_report_*.md",
        ],
        root=reports_dir,
    )[: int(args.limit)]
    print(f"Latest reports in {reports_dir}")
    print("=" * 60)
    if not rows:
        print("No report artifacts found.")
        return 0
    for path in rows:
        print(path)
    return 0


def _run_status_leaderboard(args: argparse.Namespace) -> int:
    reports_dir = Path(args.reports_dir).expanduser().resolve()
    rows = latest_paths(["**/simulation_leaderboard_*.csv"], root=reports_dir)
    if not rows:
        print("No simulation leaderboard CSV found.")
        return 0
    leaderboard = rows[0]
    print(f"Leaderboard: {leaderboard}")
    print("=" * 60)
    with leaderboard.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader, start=1):
            if idx > int(args.top):
                break
            strategy = str(row.get("strategy", "n/a"))
            market = str(row.get("market", "n/a"))
            quality = float(row.get("avg_quality_score", 0.0))
            print(f"{idx}. {strategy:20s} | {market:10s} | quality={quality:.4f}")
    return 0


def _run_status_readiness(args: argparse.Namespace) -> int:
    path = Path(args.gap_backlog).expanduser().resolve()
    if not path.exists():
        print(f"Missing backlog file: {path}")
        return 1

    lines = path.read_text(encoding="utf-8").splitlines()
    counts: dict[str, int] = {"P0": 0, "P1": 0, "P2": 0}
    for idx, line in enumerate(lines):
        token = line.strip()
        if token in {"## P0", "## P1", "## P2"} and idx + 2 < len(lines):
            count_line = lines[idx + 2].strip()
            if count_line.startswith("Count: **") and count_line.endswith("**"):
                counts[token.removeprefix("## ").strip()] = int(
                    count_line.removeprefix("Count: **").removesuffix("**")
                )
    print("SRS Gap Readiness")
    print("=" * 60)
    for key in ("P0", "P1", "P2"):
        print(f"{key}: {counts[key]}")
    if counts["P0"] > 0:
        return 2
    if counts["P1"] > 0:
        return 1
    return 0


def _run_notify_test(args: argparse.Namespace) -> int:
    channel = str(args.channel).strip().lower()
    message = str(args.message).strip()
    if channel == "stdout":
        print(f"[NOTIFY:{channel}] {message}")
        return 0

    channels = NotificationChannels(
        discord_webhook_url=str(args.discord_webhook or os.getenv("PQTS_DISCORD_WEBHOOK_URL", "")),
        telegram_bot_token=str(args.telegram_token or os.getenv("PQTS_TELEGRAM_BOT_TOKEN", "")),
        telegram_chat_id=str(args.telegram_chat_id or os.getenv("PQTS_TELEGRAM_CHAT_ID", "")),
    )
    dispatcher = NotificationDispatcher(
        channels,
        dedupe_ttl_seconds=1,
        min_interval_seconds=0,
        redis_url="",
    )
    payload = dispatcher.dispatch(message, event_key=f"notify_test:{channel}:{_utc_stamp()}")
    attempts = payload.get("attempts", [])
    selected = [row for row in attempts if str(row.get("channel")) == channel]
    if not selected:
        print(f"Channel not configured: {channel}")
        return 2
    row = selected[0]
    ok = bool(row.get("ok")) and bool(row.get("sent"))
    print(json.dumps(row, sort_keys=True))
    return 0 if ok else 1


def _run_explain_block(args: argparse.Namespace) -> int:
    reason = str(args.reason).strip()
    explanation = explain_block_reason(reason)
    print(f"{reason}: {explanation}")
    return 0


def _run_artifacts_latest(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    rows = latest_paths(
        [
            "**/template_run_*.json",
            "**/template_run_diff_*.diff",
            "**/simulation_suite_*.json",
            "**/paper_campaign_*.json",
        ],
        root=root,
    )[: int(args.limit)]
    print(f"Latest artifacts in {root}")
    print("=" * 60)
    if not rows:
        print("No artifacts found.")
        return 0
    for path in rows:
        print(path)
    return 0


def _run_new_strategy(args: argparse.Namespace) -> int:
    name = str(args.name).strip()
    if not name:
        print("Strategy name is required.")
        return 2

    try:
        payload = scaffold_strategy_plugin(
            name=name,
            out_root=str(args.out_dir),
            template=str(args.template),
            force=bool(args.force),
        )
    except FileExistsError as exc:
        print(str(exc))
        return 2

    print("Strategy plugin scaffold created")
    print("=" * 60)
    print(f"Plugin id: {payload['plugin_id']}")
    print(f"Directory: {payload['plugin_dir']}")
    print(f"Manifest: {payload['manifest']}")
    print(f"Strategy module: {payload['strategy_module']}")
    print(f"README: {payload['readme']}")
    _print_next_steps(
        [
            f"Implement signal logic in {payload['strategy_module']}",
            f"Update metadata in {payload['manifest']}",
            "Add tests under tests/plugins/ and run pytest.",
        ]
    )
    return 0


def build_first_success_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pqts",
        description=(
            "PQTS first-success CLI. Use `pqts run ...` for the legacy direct runtime path."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize a safe local workspace.")
    init_parser.add_argument("--workspace", default=".")
    init_parser.add_argument("--output", choices=["table", "json"], default="table")
    init_parser.set_defaults(handler=_run_init)

    demo_parser = subparsers.add_parser(
        "demo", help="Run a fast deterministic simulation demo with safe defaults."
    )
    demo_parser.add_argument("--config", default="config/paper.yaml")
    demo_parser.add_argument("--markets", default="crypto,equities,forex")
    demo_parser.add_argument("--strategies", default="market_making")
    demo_parser.add_argument("--cycles", type=int, default=6)
    demo_parser.add_argument("--readiness-every", type=int, default=3)
    demo_parser.add_argument("--symbols-per-market", type=int, default=1)
    demo_parser.add_argument("--risk-profile", default="balanced")
    demo_parser.add_argument("--out-dir", default="data/reports/demo")
    demo_parser.add_argument("--telemetry-log", default="data/analytics/simulation_events.jsonl")
    demo_parser.add_argument("--tca-dir", default="data/tca/simulation")
    demo_parser.add_argument("--output", choices=["table", "json"], default="table")
    demo_parser.set_defaults(handler=_run_demo)

    backtest_parser = subparsers.add_parser(
        "backtest",
        help="Run a template backtest-like simulation suite (code-visible artifact path).",
    )
    backtest_parser.add_argument("template", nargs="?", default="momentum")
    backtest_parser.add_argument("--config", default="config/paper.yaml")
    backtest_parser.add_argument("--market", default="crypto")
    backtest_parser.add_argument("--cycles", type=int, default=12)
    backtest_parser.add_argument("--readiness-every", type=int, default=4)
    backtest_parser.add_argument("--symbols-per-market", type=int, default=1)
    backtest_parser.add_argument("--risk-profile", default="balanced")
    backtest_parser.add_argument("--out-dir", default="data/reports/backtest")
    backtest_parser.add_argument("--telemetry-log", default="data/analytics/simulation_events.jsonl")
    backtest_parser.add_argument("--tca-dir", default="data/tca/simulation")
    backtest_parser.add_argument("--output", choices=["table", "json"], default="table")
    backtest_parser.set_defaults(handler=_run_backtest)

    paper_parser = subparsers.add_parser(
        "paper", help="Start a bounded paper campaign using local simulation controls."
    )
    paper_parser.add_argument("action", nargs="?", default="start", choices=["start"])
    paper_parser.add_argument("--config", default="config/paper.yaml")
    paper_parser.add_argument("--cycles", type=int, default=10)
    paper_parser.add_argument("--sleep-seconds", type=float, default=0.0)
    paper_parser.add_argument("--notional-usd", type=float, default=125.0)
    paper_parser.add_argument("--readiness-every", type=int, default=5)
    paper_parser.add_argument("--symbols", default="")
    paper_parser.add_argument("--risk-profile", default="balanced")
    paper_parser.add_argument("--out-dir", default="data/reports/paper")
    paper_parser.add_argument("--output", choices=["table", "json"], default="table")
    paper_parser.set_defaults(handler=_run_paper_start)

    skills_parser = subparsers.add_parser(
        "skills",
        help="Discover SKILL.md packages and generate raw install URLs.",
    )
    skills_subparsers = skills_parser.add_subparsers(dest="skills_action", required=True)

    skills_list_parser = skills_subparsers.add_parser("list", help="List local skill packages.")
    skills_list_parser.add_argument("--skills-dir", default=str(REPO_ROOT / "skills"))
    skills_list_parser.add_argument("--output", choices=["table", "json"], default="table")
    skills_list_parser.set_defaults(handler=_run_skills_list)

    skills_urls_parser = skills_subparsers.add_parser(
        "urls",
        help="Emit raw GitHub URLs for skill package installs.",
    )
    skills_urls_parser.add_argument("--skills-dir", default=str(REPO_ROOT / "skills"))
    skills_urls_parser.add_argument("--repo-base-url", default=_default_repo_base_url())
    skills_urls_parser.add_argument("--output", choices=["table", "json"], default="table")
    skills_urls_parser.set_defaults(handler=_run_skills_urls)

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Run environment and workspace preflight checks.",
    )
    doctor_parser.add_argument("--workspace", default=".")
    doctor_parser.add_argument("--config", default="config/paper.yaml")
    doctor_parser.add_argument("--fix", action="store_true")
    doctor_parser.add_argument("--output", choices=["table", "json"], default="table")
    doctor_parser.set_defaults(handler=_run_doctor)

    quickstart_parser = subparsers.add_parser(
        "quickstart",
        help="Generate or execute a full beginner-to-paper quickstart plan.",
    )
    quickstart_parser.add_argument("--workspace", default=".")
    quickstart_parser.add_argument("--report-root", default="data/reports/quickstart")
    quickstart_parser.add_argument("--demo-cycles", type=int, default=4)
    quickstart_parser.add_argument("--backtest-cycles", type=int, default=8)
    quickstart_parser.add_argument("--paper-cycles", type=int, default=8)
    quickstart_parser.add_argument("--execute", action="store_true")
    quickstart_parser.add_argument("--output", choices=["table", "json"], default="table")
    quickstart_parser.set_defaults(handler=_run_quickstart)

    strategies_parser = subparsers.add_parser(
        "strategies",
        help="List and explain strategy templates for beginner/pro users.",
    )
    strategies_subparsers = strategies_parser.add_subparsers(dest="strategies_action", required=True)

    strategies_list_parser = strategies_subparsers.add_parser("list", help="List strategy catalog.")
    strategies_list_parser.add_argument("--output", choices=["table", "json"], default="table")
    strategies_list_parser.set_defaults(handler=_run_strategies_list)

    strategies_explain_parser = strategies_subparsers.add_parser(
        "explain",
        help="Explain one strategy in plain language.",
    )
    strategies_explain_parser.add_argument("strategy")
    strategies_explain_parser.add_argument("--output", choices=["table", "json"], default="table")
    strategies_explain_parser.set_defaults(handler=_run_strategies_explain)

    risk_parser = subparsers.add_parser(
        "risk",
        help="List and recommend risk profiles by operator context.",
    )
    risk_subparsers = risk_parser.add_subparsers(dest="risk_action", required=True)

    risk_list_parser = risk_subparsers.add_parser("list", help="List risk profile catalog.")
    risk_list_parser.add_argument("--output", choices=["table", "json"], default="table")
    risk_list_parser.set_defaults(handler=_run_risk_list)

    risk_recommend_parser = risk_subparsers.add_parser(
        "recommend",
        help="Recommend a risk profile for user experience + capital.",
    )
    risk_recommend_parser.add_argument("--experience", default="beginner")
    risk_recommend_parser.add_argument("--capital-usd", type=float, default=5_000.0)
    risk_recommend_parser.add_argument("--automation", choices=["manual", "hybrid", "auto"], default="manual")
    risk_recommend_parser.add_argument("--output", choices=["table", "json"], default="table")
    risk_recommend_parser.set_defaults(handler=_run_risk_recommend)

    status_parser = subparsers.add_parser(
        "status",
        help="Inspect latest reports, leaderboard snapshots, and SRS readiness.",
    )
    status_subparsers = status_parser.add_subparsers(dest="status_action", required=True)

    status_reports_parser = status_subparsers.add_parser("reports", help="Show latest report artifacts.")
    status_reports_parser.add_argument("--reports-dir", default="data/reports")
    status_reports_parser.add_argument("--limit", type=int, default=8)
    status_reports_parser.add_argument("--output", choices=["table", "json"], default="table")
    status_reports_parser.set_defaults(handler=_run_status_reports)

    status_leaderboard_parser = status_subparsers.add_parser(
        "leaderboard",
        help="Show top rows from latest simulation leaderboard CSV.",
    )
    status_leaderboard_parser.add_argument("--reports-dir", default="data/reports")
    status_leaderboard_parser.add_argument("--top", type=int, default=5)
    status_leaderboard_parser.add_argument("--output", choices=["table", "json"], default="table")
    status_leaderboard_parser.set_defaults(handler=_run_status_leaderboard)

    status_readiness_parser = status_subparsers.add_parser(
        "readiness",
        help="Summarize P0/P1/P2 SRS gap counts.",
    )
    status_readiness_parser.add_argument("--gap-backlog", default="docs/SRS_GAP_BACKLOG.md")
    status_readiness_parser.add_argument("--output", choices=["table", "json"], default="table")
    status_readiness_parser.set_defaults(handler=_run_status_readiness)

    notify_parser = subparsers.add_parser(
        "notify",
        help="Send a test notification to stdout/telegram/discord.",
    )
    notify_subparsers = notify_parser.add_subparsers(dest="notify_action", required=True)
    notify_test_parser = notify_subparsers.add_parser("test", help="Send test notification.")
    notify_test_parser.add_argument(
        "--channel",
        choices=["stdout", "telegram", "discord"],
        default="stdout",
    )
    notify_test_parser.add_argument("--message", default="[PQTS TEST] Notifications channel check.")
    notify_test_parser.add_argument("--discord-webhook", default="")
    notify_test_parser.add_argument("--telegram-token", default="")
    notify_test_parser.add_argument("--telegram-chat-id", default="")
    notify_test_parser.add_argument("--output", choices=["table", "json"], default="table")
    notify_test_parser.set_defaults(handler=_run_notify_test)

    explain_parser = subparsers.add_parser(
        "explain",
        help="Explain common system gate outcomes in plain language.",
    )
    explain_subparsers = explain_parser.add_subparsers(dest="explain_action", required=True)
    explain_block_parser = explain_subparsers.add_parser(
        "block",
        help="Explain one block reason code.",
    )
    explain_block_parser.add_argument("reason")
    explain_block_parser.add_argument("--output", choices=["table", "json"], default="table")
    explain_block_parser.set_defaults(handler=_run_explain_block)

    artifacts_parser = subparsers.add_parser(
        "artifacts",
        help="Inspect latest generated artifacts.",
    )
    artifacts_subparsers = artifacts_parser.add_subparsers(dest="artifacts_action", required=True)
    artifacts_latest_parser = artifacts_subparsers.add_parser("latest", help="List latest artifacts.")
    artifacts_latest_parser.add_argument("--root", default="data")
    artifacts_latest_parser.add_argument("--limit", type=int, default=10)
    artifacts_latest_parser.add_argument("--output", choices=["table", "json"], default="table")
    artifacts_latest_parser.set_defaults(handler=_run_artifacts_latest)

    new_strategy_parser = subparsers.add_parser(
        "new-strategy",
        help="Scaffold a strategy plugin package for extension development.",
    )
    new_strategy_parser.add_argument("name", help="Human-readable strategy name")
    new_strategy_parser.add_argument("--out-dir", default="plugins/strategies")
    new_strategy_parser.add_argument("--template", default="basic")
    new_strategy_parser.add_argument("--force", action="store_true")
    new_strategy_parser.add_argument("--output", choices=["table", "json"], default="table")
    new_strategy_parser.set_defaults(handler=_run_new_strategy)

    return parser


def run_first_success_cli(argv: Sequence[str]) -> int:
    parser = build_first_success_parser()
    args = parser.parse_args(list(argv))
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 2
    output_mode = str(getattr(args, "output", "table")).strip().lower()
    if output_mode != "json":
        return int(handler(args))

    stdout_buffer = io.StringIO()
    try:
        with redirect_stdout(stdout_buffer):
            return_code = int(handler(args))
        payload = {
            "ok": return_code == 0,
            "command": str(getattr(args, "command", "")),
            "return_code": int(return_code),
            "stdout": [line for line in stdout_buffer.getvalue().splitlines() if line.strip()],
        }
        if return_code != 0:
            payload["error"] = "command_failed"
        print(json.dumps(payload, sort_keys=True))
        return return_code
    except Exception as exc:
        payload = {
            "ok": False,
            "command": str(getattr(args, "command", "")),
            "return_code": 2,
            "error": str(exc),
            "stdout": [line for line in stdout_buffer.getvalue().splitlines() if line.strip()],
        }
        print(json.dumps(payload, sort_keys=True))
        return 2
