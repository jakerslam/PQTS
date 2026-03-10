"""CLI tests for execution latency benchmark script."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import benchmark_execution_latency


def test_benchmark_cli_requires_native_when_flagged(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["benchmark_execution_latency.py", "--require-native"])
    monkeypatch.setattr(benchmark_execution_latency, "native_available", lambda: False)
    assert benchmark_execution_latency.main() == 2


def test_benchmark_cli_writes_summary_payload(tmp_path, monkeypatch):
    out_dir = tmp_path / "bench"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark_execution_latency.py",
            "--out-dir",
            str(out_dir),
            "--orders",
            "5",
        ],
    )

    async def _fake_run(_args):
        return {
            "timestamp_utc": "2026-03-10T00:00:00+00:00",
            "environment": {
                "python": "3.12",
                "platform": "test",
                "native_available": True,
                "native_version": "pqts_hotpath 0.1.0",
            },
            "benchmark": {
                "orders": 5,
                "symbol": "BTC-USD",
                "venue": "binance",
                "price": 50000.0,
                "target_p95_ms": 200.0,
            },
            "result": {
                "success_count": 5,
                "failure_count": 0,
                "latency_ms": {"min": 1.0, "p50": 2.0, "p95": 5.0, "p99": 6.0, "max": 7.0, "avg": 3.0},
                "target_met": True,
            },
        }

    monkeypatch.setattr(benchmark_execution_latency, "_run_benchmark", _fake_run)
    assert benchmark_execution_latency.main() == 0

    outputs = sorted(out_dir.glob("execution_latency_benchmark_*.json"))
    assert outputs
    payload = json.loads(outputs[-1].read_text(encoding="utf-8"))
    assert payload["result"]["latency_ms"]["p95"] == 5.0
