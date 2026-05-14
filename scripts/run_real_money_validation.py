#!/usr/bin/env python3
"""Run the real-data validation ladder before any live-money decision."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if SRC.exists():
    src_str = str(SRC)
    if src_str not in sys.path:
        sys.path[:] = [src_str, *sys.path]
if str(ROOT) not in sys.path:
    sys.path[:] = [str(ROOT), *sys.path]

from research.data_lake import DataLakeQualityGate, MarketDataLake  # noqa: E402
from research.historical_data import HistoricalDataDownloader  # noqa: E402
from research.tournament import (  # noqa: E402
    LakeSymbolSource,
    StrategyTournamentRunner,
    TournamentConfig,
)


_INTERVAL_SECONDS = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1_800,
    "1h": 3_600,
    "2h": 7_200,
    "4h": 14_400,
    "6h": 21_600,
    "8h": 28_800,
    "12h": 43_200,
    "1d": 86_400,
}


def _parse_datetime(value: str) -> datetime:
    token = str(value).strip()
    if not token:
        raise ValueError("datetime value is required")
    if "T" not in token:
        parsed = datetime.strptime(token, "%Y-%m-%d")
        return parsed.replace(tzinfo=timezone.utc)
    if token.endswith("Z"):
        token = token[:-1] + "+00:00"
    parsed = datetime.fromisoformat(token)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_csv(value: str) -> List[str]:
    return [token.strip() for token in str(value or "").split(",") if token.strip()]


def _interval_seconds(interval: str) -> int:
    if interval not in _INTERVAL_SECONDS:
        raise ValueError(f"Unsupported interval for validation ladder: {interval}")
    return int(_INTERVAL_SECONDS[interval])


def _run_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _resolve_run_dir(args: argparse.Namespace) -> Path:
    if str(args.run_dir or "").strip():
        return Path(args.run_dir)
    run_id = str(args.run_id or "").strip() or _run_stamp()
    return Path(args.out_dir) / f"real_money_validation_{run_id}"


def _load_yaml_config(path: str) -> Dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object YAML config: {path}")
    return payload


def _prepare_agent_config(
    *,
    base_config: Dict[str, Any],
    run_dir: Path,
    args: argparse.Namespace,
) -> Dict[str, Any]:
    config = copy.deepcopy(base_config)
    config["db_path"] = str(run_dir / "research.db")
    config["search_budget"] = int(args.search_budget)
    config["top_performers"] = int(args.top_performers)

    analytics_cfg = dict(config.get("analytics", {}) or {})
    analytics_cfg["report_dir"] = str(run_dir / "research_reports")
    analytics_cfg["artifact_registry_dir"] = str(run_dir / "research_artifacts")
    config["analytics"] = analytics_cfg

    walk_forward_cfg = dict(config.get("walk_forward", {}) or {})
    walk_forward_cfg.update(
        {
            "train_years": float(args.wf_train_years),
            "validate_years": float(args.wf_validate_years),
            "test_years": float(args.wf_test_years),
            "step_years": float(args.wf_step_years),
        }
    )
    config["walk_forward"] = walk_forward_cfg
    return config


def _quality_gate_from_args(args: argparse.Namespace) -> DataLakeQualityGate:
    return DataLakeQualityGate(
        min_completeness=float(args.min_completeness),
        max_missing_intervals=int(args.max_missing_intervals),
        require_monotonic=not bool(args.allow_non_monotonic),
    )


def _download_symbol_frame(
    *,
    downloader: HistoricalDataDownloader,
    venue: str,
    symbol: str,
    interval: str,
    start: datetime,
    end: datetime,
    fmt: str,
    cache_mode: str,
):
    frame = None
    if cache_mode == "use":
        frame = downloader.load_cached_dataset(
            venue=venue,
            symbol=symbol,
            interval=interval,
            start=start,
            end=end,
            fmt=fmt,
        )
    cache_hit = frame is not None
    if frame is None:
        if venue == "coinbase":
            frame = downloader.download_coinbase_ohlcv(
                product_id=symbol,
                interval=interval,
                start=start,
                end=end,
            )
        elif venue == "binance":
            frame = downloader.download_binance_ohlcv(
                symbol=symbol,
                interval=interval,
                start=start,
                end=end,
            )
        else:
            raise ValueError(f"Unsupported venue: {venue}")
    return frame, cache_hit


def _prepare_historical_lake(
    *,
    args: argparse.Namespace,
    run_dir: Path,
    start: datetime,
    end: datetime,
) -> tuple[Path, List[Dict[str, Any]]]:
    symbols = _parse_csv(args.symbols)
    if not symbols:
        raise ValueError("--symbols must include at least one symbol")

    lake_root = Path(args.lake_root) if str(args.lake_root or "").strip() else run_dir / "lake"
    downloader = HistoricalDataDownloader(
        output_dir=args.historical_dir,
        max_retries=int(args.max_retries),
        retry_backoff_seconds=float(args.retry_backoff_seconds),
    )
    lake = MarketDataLake(str(lake_root))
    gate = _quality_gate_from_args(args)
    interval_seconds = _interval_seconds(args.interval)
    rows: List[Dict[str, Any]] = []

    for symbol in symbols:
        frame, cache_hit = _download_symbol_frame(
            downloader=downloader,
            venue=str(args.venue),
            symbol=symbol,
            interval=str(args.interval),
            start=start,
            end=end,
            fmt=str(args.format),
            cache_mode=str(args.cache_mode),
        )
        downloader_quality = downloader.quality_summary(frame, interval=str(args.interval))
        saved_path = downloader.save_dataset(
            frame,
            venue=str(args.venue),
            symbol=symbol,
            interval=str(args.interval),
            start=start,
            end=end,
            fmt=str(args.format),
        )
        partitions = lake.write_ohlcv(frame, venue=str(args.venue), symbol=symbol)
        loaded = lake.load_ohlcv_range(
            venue=str(args.venue),
            symbol=symbol,
            start=start,
            end=end,
        )
        lake_quality = MarketDataLake.quality_summary(
            loaded,
            interval_seconds=interval_seconds,
        )
        gate_payload = MarketDataLake.enforce_quality_gate(
            summary=lake_quality,
            gate=gate,
        )
        rows.append(
            {
                "venue": str(args.venue),
                "symbol": symbol,
                "interval": str(args.interval),
                "cache": "hit" if cache_hit else "miss",
                "historical_path": str(saved_path),
                "lake_partitions_written": len(partitions),
                "downloader_quality": asdict(downloader_quality),
                "lake_quality_gate": gate_payload,
            }
        )
    return lake_root, rows


def _run_validation_payload_builder(
    *,
    args: argparse.Namespace,
    run_dir: Path,
) -> Dict[str, Any]:
    stdout_path = run_dir / "research_validation_payload.stdout.txt"
    stderr_path = run_dir / "research_validation_payload.stderr.txt"
    command = [
        sys.executable,
        str(ROOT / "scripts" / "build_research_validation_payload.py"),
        "--reports-dir",
        str(run_dir / "research_reports"),
        "--out-dir",
        str(run_dir),
        "--min-purged-cv-sharpe",
        str(args.min_purged_cv_sharpe),
        "--min-walk-forward-sharpe",
        str(args.min_walk_forward_sharpe),
        "--min-deflated-sharpe",
        str(args.min_deflated_sharpe),
        "--min-parameter-stability-score",
        str(args.min_parameter_stability_score),
        "--min-regime-robustness-score",
        str(args.min_regime_robustness_score),
        "--max-expected-alpha-bps",
        str(args.max_expected_alpha_bps),
    ]
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")

    parsed: Dict[str, Any] = {}
    for line in reversed([row.strip() for row in completed.stdout.splitlines() if row.strip()]):
        if line.startswith("{"):
            parsed = json.loads(line)
            break

    return {
        "returncode": int(completed.returncode),
        "command": command,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "payload_path": str(parsed.get("payload_path", "")),
        "payload": parsed.get("payload", {}),
    }


def _payload_is_promotable(payload: Dict[str, Any]) -> bool:
    return bool(
        payload.get("purged_cv_passed")
        and payload.get("walk_forward_passed")
        and payload.get("deflated_sharpe_passed")
        and payload.get("parameter_stability_passed")
        and payload.get("regime_robustness_passed")
        and float(payload.get("expected_alpha_bps", 0.0) or 0.0) > 0.0
    )


def _build_paper_command(
    *,
    args: argparse.Namespace,
    run_dir: Path,
    research_validation_path: Path,
) -> List[str]:
    return [
        sys.executable,
        str(ROOT / "scripts" / "run_paper_campaign.py"),
        "--config",
        str(args.paper_config),
        "--symbols",
        str(args.symbols),
        "--cycles",
        str(args.paper_cycles),
        "--sleep-seconds",
        str(args.paper_sleep_seconds),
        "--notional-usd",
        str(args.paper_notional_usd),
        "--readiness-every",
        str(args.paper_readiness_every),
        "--out-dir",
        str(run_dir / "live_paper_smoke"),
        "--tca-db-path",
        str(run_dir / "live_paper_smoke_tca.csv"),
        "--research-validation",
        str(research_validation_path),
        "--require-research-alpha",
        "--min-days",
        str(args.paper_min_days),
        "--min-fills",
        str(args.paper_min_fills),
        "--promotion-min-days",
        str(args.paper_promotion_min_days),
        "--promotion-max-days",
        str(args.paper_promotion_max_days),
        "--max-p95-slippage-bps",
        str(args.paper_max_p95_slippage_bps),
        "--max-mape-pct",
        str(args.paper_max_mape_pct),
        "--calibration-min-samples",
        str(args.paper_calibration_min_samples),
        "--promotion-min-purged-cv-sharpe",
        str(args.min_purged_cv_sharpe),
        "--promotion-min-walk-forward-sharpe",
        str(args.min_walk_forward_sharpe),
        "--promotion-min-deflated-sharpe",
        str(args.min_deflated_sharpe),
        "--promotion-min-parameter-stability-score",
        str(args.min_parameter_stability_score),
        "--promotion-min-regime-robustness-score",
        str(args.min_regime_robustness_score),
    ]


def _parse_last_json_line(stdout: str) -> Dict[str, Any]:
    for line in reversed([row.strip() for row in stdout.splitlines() if row.strip()]):
        if line.startswith("{"):
            return json.loads(line)
    return {}


def _run_live_paper_smoke(
    *,
    args: argparse.Namespace,
    run_dir: Path,
    research_validation_path: str,
    research_promotable: bool,
) -> Dict[str, Any]:
    if not bool(args.run_paper_smoke):
        return {"attempted": False, "reason": "disabled"}
    if not research_promotable:
        return {"attempted": False, "reason": "research_gate_not_promotable"}
    if not research_validation_path:
        return {"attempted": False, "reason": "missing_research_validation_payload"}

    stdout_path = run_dir / "live_paper_smoke.stdout.txt"
    stderr_path = run_dir / "live_paper_smoke.stderr.txt"
    command = _build_paper_command(
        args=args,
        run_dir=run_dir,
        research_validation_path=Path(research_validation_path),
    )
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
        timeout=float(args.paper_timeout_seconds),
    )
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")

    return {
        "attempted": True,
        "returncode": int(completed.returncode),
        "command": command,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "result": _parse_last_json_line(completed.stdout),
    }


def _live_money_assessment(
    *,
    research_promotable: bool,
    paper_smoke: Dict[str, Any],
) -> Dict[str, Any]:
    if not research_promotable:
        return {
            "can_deploy_live_now": False,
            "recommended_action": "hold",
            "reason": "No strategy passed the research validation payload gates.",
        }
    if not paper_smoke.get("attempted"):
        return {
            "can_deploy_live_now": False,
            "recommended_action": "run_research_alpha_paper",
            "reason": "Historical gates found a candidate, but live-data paper validation has not run.",
        }
    if int(paper_smoke.get("returncode", 1)) != 0:
        return {
            "can_deploy_live_now": False,
            "recommended_action": "fix_paper_validation",
            "reason": "The research-alpha-backed live-data paper smoke did not complete cleanly.",
        }
    return {
        "can_deploy_live_now": False,
        "recommended_action": "continue_30_90d_paper_validation",
        "reason": "Live-money promotion still requires minimum paper duration, fill count, slippage, and kill-switch gates.",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venue", choices=["coinbase", "binance"], default="coinbase")
    parser.add_argument("--symbols", default="BTC-USD,ETH-USD,SOL-USD")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD or ISO-8601 UTC timestamp")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD or ISO-8601 UTC timestamp")
    parser.add_argument("--historical-dir", default="data/historical")
    parser.add_argument("--lake-root", default="")
    parser.add_argument("--out-dir", default="data/reports")
    parser.add_argument("--run-dir", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--format", choices=["csv", "parquet"], default="csv")
    parser.add_argument("--cache-mode", choices=["use", "refresh"], default="use")
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--retry-backoff-seconds", type=float, default=0.75)

    parser.add_argument("--agent-config", default="src/research/agent_config.yaml")
    parser.add_argument(
        "--strategy-types",
        default=(
            "market_making,stat_arb,swing_trend,hold_carry,"
            "cross_sectional_momentum,adaptive_trend,drawdown_reversion,markov_regime"
        ),
    )
    parser.add_argument("--search-budget", type=int, default=60)
    parser.add_argument("--top-performers", type=int, default=5)
    parser.add_argument("--wf-train-years", type=float, default=1.0)
    parser.add_argument("--wf-validate-years", type=float, default=0.25)
    parser.add_argument("--wf-test-years", type=float, default=0.25)
    parser.add_argument("--wf-step-years", type=float, default=0.25)

    parser.add_argument("--min-completeness", type=float, default=0.995)
    parser.add_argument("--max-missing-intervals", type=int, default=0)
    parser.add_argument("--allow-non-monotonic", action="store_true")

    parser.add_argument("--min-purged-cv-sharpe", type=float, default=1.0)
    parser.add_argument("--min-walk-forward-sharpe", type=float, default=1.0)
    parser.add_argument("--min-deflated-sharpe", type=float, default=0.8)
    parser.add_argument("--min-parameter-stability-score", type=float, default=0.55)
    parser.add_argument("--min-regime-robustness-score", type=float, default=0.55)
    parser.add_argument("--max-expected-alpha-bps", type=float, default=25.0)

    parser.add_argument("--run-paper-smoke", action="store_true")
    parser.add_argument("--paper-config", default="config/live_data.yaml")
    parser.add_argument("--paper-cycles", type=int, default=12)
    parser.add_argument("--paper-sleep-seconds", type=float, default=2.0)
    parser.add_argument("--paper-notional-usd", type=float, default=50.0)
    parser.add_argument("--paper-readiness-every", type=int, default=4)
    parser.add_argument("--paper-timeout-seconds", type=float, default=900.0)
    parser.add_argument("--paper-min-days", type=int, default=30)
    parser.add_argument("--paper-min-fills", type=int, default=200)
    parser.add_argument("--paper-promotion-min-days", type=int, default=30)
    parser.add_argument("--paper-promotion-max-days", type=int, default=90)
    parser.add_argument("--paper-max-p95-slippage-bps", type=float, default=20.0)
    parser.add_argument("--paper-max-mape-pct", type=float, default=35.0)
    parser.add_argument("--paper-calibration-min-samples", type=int, default=10)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    start = _parse_datetime(args.start)
    end = _parse_datetime(args.end)
    if end <= start:
        raise ValueError("--end must be strictly after --start")

    run_dir = _resolve_run_dir(args)
    run_dir.mkdir(parents=True, exist_ok=True)

    lake_root, data_rows = _prepare_historical_lake(
        args=args,
        run_dir=run_dir,
        start=start,
        end=end,
    )
    agent_config = _prepare_agent_config(
        base_config=_load_yaml_config(args.agent_config),
        run_dir=run_dir,
        args=args,
    )
    strategy_types = _parse_csv(args.strategy_types)
    sources = [
        LakeSymbolSource(venue=str(args.venue), symbol=symbol) for symbol in _parse_csv(args.symbols)
    ]

    runner = StrategyTournamentRunner(
        agent_config=agent_config,
        lake_root=str(lake_root),
        out_dir=str(run_dir),
        config=TournamentConfig(
            interval_seconds=_interval_seconds(args.interval),
            quality_gate=_quality_gate_from_args(args),
            auto_promote_canary=False,
        ),
    )
    tournament = runner.run_once(
        strategy_types=strategy_types,
        sources=sources,
        start=start,
        end=end,
    )
    validation = _run_validation_payload_builder(args=args, run_dir=run_dir)
    research_promotable = _payload_is_promotable(dict(validation.get("payload", {}) or {}))
    paper_smoke = _run_live_paper_smoke(
        args=args,
        run_dir=run_dir,
        research_validation_path=str(validation.get("payload_path", "")),
        research_promotable=research_promotable,
    )

    evidence = {
        "timestamp": _iso(datetime.now(timezone.utc)),
        "run_dir": str(run_dir),
        "period": {"start": _iso(start), "end": _iso(end), "interval": str(args.interval)},
        "venue": str(args.venue),
        "symbols": _parse_csv(args.symbols),
        "historical_data": data_rows,
        "research": {
            "tournament_report_path": str(tournament.get("report_path", "")),
            "summary": tournament.get("research_report", {}).get("summary", {}),
            "performance": tournament.get("research_report", {}).get("performance", {}),
            "top_strategies": tournament.get("research_report", {}).get("top_strategies", []),
            "analytics": tournament.get("research_report", {}).get("analytics", {}),
        },
        "validation": validation,
        "research_promotable": bool(research_promotable),
        "paper_smoke": paper_smoke,
        "live_money_assessment": _live_money_assessment(
            research_promotable=research_promotable,
            paper_smoke=paper_smoke,
        ),
    }

    report_path = run_dir / f"real_money_validation_report_{_run_stamp()}.json"
    report_path.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    print(report_path)
    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "research_promotable": bool(research_promotable),
                "live_money_assessment": evidence["live_money_assessment"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
