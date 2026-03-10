"""Benchmark order submit latency on the router execution path."""

from __future__ import annotations

import argparse
import asyncio
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.hotpath_runtime import native_available  # noqa: E402
from execution.paper_fill_model import (  # noqa: E402
    MicrostructurePaperFillProvider,
    PaperFillModelConfig,
)
from execution.risk_aware_router import RiskAwareRouter  # noqa: E402
from execution.smart_router import OrderRequest, OrderType  # noqa: E402
from risk.kill_switches import RiskLimits  # noqa: E402


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark RiskAwareRouter submit_order latency with reproducible output."
    )
    parser.add_argument("--orders", type=int, default=500)
    parser.add_argument("--target-p95-ms", type=float, default=200.0)
    parser.add_argument("--out-dir", default="results/native_benchmarks")
    parser.add_argument("--symbol", default="BTC-USD")
    parser.add_argument("--venue", default="binance")
    parser.add_argument("--price", type=float, default=50000.0)
    parser.add_argument("--base-qty", type=float, default=0.05)
    parser.add_argument("--require-native", action="store_true")
    return parser.parse_args()


def _portfolio_snapshot(price: float) -> dict:
    return {
        "positions": {"BTC": 0.25},
        "prices": {"BTC": float(price)},
        "total_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "realized_pnl": 0.0,
        "gross_exposure": float(price) * 0.25,
        "net_exposure": float(price) * 0.25,
        "leverage": 0.25,
        "open_orders": [],
    }


def _strategy_inputs() -> tuple[dict, list[float]]:
    strategy_returns = {
        "s1": np.linspace(-0.01, 0.01, 30),
        "s2": np.cos(np.linspace(0.0, 2.0 * np.pi, 30)) * 0.005,
    }
    portfolio_changes = list(np.linspace(-50.0, 50.0, 30))
    return strategy_returns, portfolio_changes


async def _run_benchmark(args: argparse.Namespace) -> dict:
    router = RiskAwareRouter(
        risk_config=RiskLimits(
            max_daily_loss_pct=0.02,
            max_drawdown_pct=0.2,
            max_gross_leverage=2.0,
        ),
        broker_config={"enabled": True},
        fill_provider=MicrostructurePaperFillProvider(
            config=PaperFillModelConfig(base_latency_ms=35.0, latency_jitter_ms=45.0)
        ),
        tca_db_path="data/tca_latency_probe.csv",
    )
    router.set_capital(100000.0, source="latency_benchmark")
    strategy_returns, portfolio_changes = _strategy_inputs()
    market_data = {
        args.venue: {
            args.symbol: {"price": float(args.price), "spread": 0.0002, "volume_24h": 2_000_000}
        },
        "order_book": {
            "bids": [(float(args.price) * 0.9998, 2.0), (float(args.price) * 0.9996, 4.0)],
            "asks": [(float(args.price) * 1.0002, 1.5), (float(args.price) * 1.0004, 3.0)],
        },
    }

    samples_ms: list[float] = []
    success = 0
    failed = 0
    for idx in range(int(max(args.orders, 1))):
        order = OrderRequest(
            symbol=args.symbol,
            side="buy",
            quantity=float(args.base_qty) + (idx % 3) * 0.01,
            order_type=OrderType.LIMIT,
            price=float(args.price),
        )
        started = time.perf_counter()
        result = await router.submit_order(
            order=order,
            market_data=market_data,
            portfolio=_portfolio_snapshot(float(args.price)),
            strategy_returns=strategy_returns,
            portfolio_changes=portfolio_changes,
        )
        elapsed = (time.perf_counter() - started) * 1000.0
        samples_ms.append(float(elapsed))
        if result.success:
            success += 1
        else:
            failed += 1

    arr = np.asarray(samples_ms, dtype=float)
    p50 = float(np.percentile(arr, 50))
    p95 = float(np.percentile(arr, 95))
    p99 = float(np.percentile(arr, 99))

    native_enabled = native_available()
    native_version = "python_fallback"
    if native_enabled:
        try:
            import pqts_hotpath as native_mod  # type: ignore

            native_version = str(native_mod.version())
        except Exception:
            native_version = "native_loaded_unknown_version"

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "native_available": native_enabled,
            "native_version": native_version,
        },
        "benchmark": {
            "orders": int(max(args.orders, 1)),
            "symbol": str(args.symbol),
            "venue": str(args.venue),
            "price": float(args.price),
            "target_p95_ms": float(args.target_p95_ms),
        },
        "result": {
            "success_count": int(success),
            "failure_count": int(failed),
            "latency_ms": {
                "min": float(arr.min()),
                "p50": p50,
                "p95": p95,
                "p99": p99,
                "max": float(arr.max()),
                "avg": float(arr.mean()),
            },
            "target_met": bool(p95 <= float(args.target_p95_ms)),
        },
    }


def main() -> int:
    args = _args()
    if args.require_native and not native_available():
        print("native hotpath is required but pqts_hotpath is not installed", file=sys.stderr)
        return 2

    payload = asyncio.run(_run_benchmark(args))

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"execution_latency_benchmark_{stamp}.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    summary = {
        "output": str(out_path),
        "native_available": payload["environment"]["native_available"],
        "p95_ms": payload["result"]["latency_ms"]["p95"],
        "target_p95_ms": payload["benchmark"]["target_p95_ms"],
        "target_met": payload["result"]["target_met"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if payload["result"]["target_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
