#!/usr/bin/env python3
"""Run standard vs agent-assisted six-month paper harness and compare outcomes."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/paper.yaml")
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--anchor-date", default="")
    parser.add_argument("--cycles-per-month", type=int, default=12)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--notional-usd", type=float, default=150.0)
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT,BTC-USD,ETH-USD")
    parser.add_argument("--risk-profile", default="balanced")
    parser.add_argument("--operator-tier", default="")
    parser.add_argument("--lookback-days", type=int, default=60)
    parser.add_argument("--min-days", type=int, default=1)
    parser.add_argument("--min-fills", type=int, default=10)
    parser.add_argument("--readiness-every", type=int, default=1)
    parser.add_argument("--max-p95-slippage-bps", type=float, default=25.0)
    parser.add_argument("--max-mape-pct", type=float, default=40.0)
    parser.add_argument("--max-reject-rate", type=float, default=1.0)
    parser.add_argument("--max-avg-reject-rate", type=float, default=0.5)
    parser.add_argument("--min-ready-months", type=int, default=1)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--out-dir", default="data/reports/paper_6m_compare")
    parser.add_argument("--tca-root", default="data/tca/paper_6m_compare")

    parser.add_argument("--agent-risk-profile", default="")
    parser.add_argument("--agent-operator-tier", default="pro")
    parser.add_argument("--agent-max-reject-rate", type=float, default=0.8)
    parser.add_argument("--agent-max-avg-reject-rate", type=float, default=0.4)
    parser.add_argument("--agent-min-ready-months", type=int, default=2)
    return parser


def _parse_summary(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        token = line.strip()
        if not token:
            continue
        try:
            payload = json.loads(token)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def _build_base_cmd(args: argparse.Namespace) -> list[str]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_paper_6m_harness.py"),
        "--config",
        str(args.config),
        "--months",
        str(int(args.months)),
        "--cycles-per-month",
        str(int(args.cycles_per_month)),
        "--sleep-seconds",
        str(float(args.sleep_seconds)),
        "--notional-usd",
        str(float(args.notional_usd)),
        "--symbols",
        str(args.symbols),
        "--risk-profile",
        str(args.risk_profile),
        "--lookback-days",
        str(int(args.lookback_days)),
        "--min-days",
        str(int(args.min_days)),
        "--min-fills",
        str(int(args.min_fills)),
        "--readiness-every",
        str(int(args.readiness_every)),
        "--max-p95-slippage-bps",
        str(float(args.max_p95_slippage_bps)),
        "--max-mape-pct",
        str(float(args.max_mape_pct)),
        "--max-reject-rate",
        str(float(args.max_reject_rate)),
        "--max-avg-reject-rate",
        str(float(args.max_avg_reject_rate)),
        "--min-ready-months",
        str(int(args.min_ready_months)),
    ]
    if str(args.anchor_date).strip():
        cmd.extend(["--anchor-date", str(args.anchor_date).strip()])
    if str(args.operator_tier).strip():
        cmd.extend(["--operator-tier", str(args.operator_tier).strip()])
    if bool(args.strict):
        cmd.append("--strict")
    return cmd


def _build_cmd_for_arm(args: argparse.Namespace, *, arm: str, out_dir: Path, tca_root: Path) -> list[str]:
    cmd = _build_base_cmd(args)
    cmd.extend(["--out-dir", str(out_dir), "--tca-root", str(tca_root)])
    if arm == "agent":
        risk_profile = str(args.agent_risk_profile).strip() or str(args.risk_profile).strip()
        cmd.extend(["--risk-profile", risk_profile])
        if str(args.agent_operator_tier).strip():
            cmd.extend(["--operator-tier", str(args.agent_operator_tier).strip()])
        cmd.extend(["--max-reject-rate", str(float(args.agent_max_reject_rate))])
        cmd.extend(["--max-avg-reject-rate", str(float(args.agent_max_avg_reject_rate))])
        cmd.extend(["--min-ready-months", str(int(args.agent_min_ready_months))])
    return cmd


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _fill_rate(total_filled: int, total_submitted: int) -> float:
    return float(total_filled) / float(total_submitted) if total_submitted > 0 else 0.0


def compare_aggregates(*, standard: dict[str, Any], agent: dict[str, Any]) -> dict[str, Any]:
    standard_submitted = _safe_int(standard.get("total_submitted"))
    standard_filled = _safe_int(standard.get("total_filled"))
    standard_reject_rate = _safe_float(standard.get("avg_reject_rate"))
    standard_ready = _safe_int(standard.get("ready_months"))
    standard_passed = bool(standard.get("passed", False))

    agent_submitted = _safe_int(agent.get("total_submitted"))
    agent_filled = _safe_int(agent.get("total_filled"))
    agent_reject_rate = _safe_float(agent.get("avg_reject_rate"))
    agent_ready = _safe_int(agent.get("ready_months"))
    agent_passed = bool(agent.get("passed", False))

    standard_fill_rate = _fill_rate(standard_filled, standard_submitted)
    agent_fill_rate = _fill_rate(agent_filled, agent_submitted)
    winner = "tie"
    if agent_fill_rate > standard_fill_rate:
        winner = "agent"
    elif standard_fill_rate > agent_fill_rate:
        winner = "standard"

    return {
        "standard": {
            "total_submitted": standard_submitted,
            "total_filled": standard_filled,
            "fill_rate": standard_fill_rate,
            "avg_reject_rate": standard_reject_rate,
            "ready_months": standard_ready,
            "passed": standard_passed,
        },
        "agent": {
            "total_submitted": agent_submitted,
            "total_filled": agent_filled,
            "fill_rate": agent_fill_rate,
            "avg_reject_rate": agent_reject_rate,
            "ready_months": agent_ready,
            "passed": agent_passed,
        },
        "delta": {
            "submitted_delta": agent_submitted - standard_submitted,
            "filled_delta": agent_filled - standard_filled,
            "fill_rate_delta": agent_fill_rate - standard_fill_rate,
            "avg_reject_rate_delta": agent_reject_rate - standard_reject_rate,
            "ready_months_delta": agent_ready - standard_ready,
            "passed_delta": int(agent_passed) - int(standard_passed),
        },
        "winner_by_fill_rate": winner,
    }


def _write_report(*, out_dir: Path, payload: dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = out_dir / f"paper_6m_agent_vs_standard_{stamp}.json"
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report_path


def _run_arm(*, cmd: list[str], arm: str) -> tuple[int, dict[str, Any], str, str]:
    completed = subprocess.run(  # noqa: S603
        cmd,
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    summary = _parse_summary(completed.stdout)
    if not summary:
        raise RuntimeError(f"failed to parse {arm} harness summary")
    return int(completed.returncode), summary, completed.stdout, completed.stderr


def main() -> int:
    args = build_parser().parse_args()
    out_dir = Path(args.out_dir)
    tca_root = Path(args.tca_root)
    standard_out = out_dir / "standard"
    agent_out = out_dir / "agent"
    standard_tca = tca_root / "standard"
    agent_tca = tca_root / "agent"

    standard_cmd = _build_cmd_for_arm(args, arm="standard", out_dir=standard_out, tca_root=standard_tca)
    agent_cmd = _build_cmd_for_arm(args, arm="agent", out_dir=agent_out, tca_root=agent_tca)

    standard_rc, standard_summary, _, _ = _run_arm(cmd=standard_cmd, arm="standard")
    agent_rc, agent_summary, _, _ = _run_arm(cmd=agent_cmd, arm="agent")

    standard_report_path = Path(str(standard_summary.get("report_path", "")).strip())
    agent_report_path = Path(str(agent_summary.get("report_path", "")).strip())
    if not standard_report_path.exists():
        raise FileNotFoundError(f"standard report path missing: {standard_report_path}")
    if not agent_report_path.exists():
        raise FileNotFoundError(f"agent report path missing: {agent_report_path}")

    standard_report = _load_json(standard_report_path)
    agent_report = _load_json(agent_report_path)
    standard_aggregate = standard_report.get("aggregate", {})
    agent_aggregate = agent_report.get("aggregate", {})
    if not isinstance(standard_aggregate, dict) or not isinstance(agent_aggregate, dict):
        raise RuntimeError("missing aggregate payload in one or more harness reports")

    comparison = compare_aggregates(standard=standard_aggregate, agent=agent_aggregate)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "harness": {
            "months": int(args.months),
            "anchor_date": str(args.anchor_date).strip() or None,
            "cycles_per_month": int(args.cycles_per_month),
            "symbols": [token.strip() for token in str(args.symbols).split(",") if token.strip()],
        },
        "commands": {
            "standard": standard_cmd,
            "agent": agent_cmd,
        },
        "reports": {
            "standard": str(standard_report_path),
            "agent": str(agent_report_path),
        },
        "comparison": comparison,
    }
    report_path = _write_report(out_dir=out_dir, payload=payload)

    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "standard_passed": bool(comparison["standard"]["passed"]),
                "agent_passed": bool(comparison["agent"]["passed"]),
                "winner_by_fill_rate": str(comparison["winner_by_fill_rate"]),
                "fill_rate_delta": float(comparison["delta"]["fill_rate_delta"]),
                "avg_reject_rate_delta": float(comparison["delta"]["avg_reject_rate_delta"]),
            },
            sort_keys=True,
        )
    )

    if bool(args.strict) and (standard_rc != 0 or agent_rc != 0):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
