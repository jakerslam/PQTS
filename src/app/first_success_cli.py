"""First-success CLI commands for quick onboarding flows."""

from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
FIRST_SUCCESS_COMMANDS = {"init", "demo", "backtest", "paper"}

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
    _print_next_steps(
        [
            "Review outputs in data/reports/backtest/",
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
    _print_next_steps(
        [
            "Inspect latest snapshot in data/reports/paper/",
            "python3 scripts/control_plane_report.py --events data/analytics/attribution_events.jsonl",
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
