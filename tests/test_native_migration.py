from __future__ import annotations

import json
from pathlib import Path

from core.native_migration import (
    MigrationEvidence,
    build_native_release_matrix,
    decide_native_migration,
    load_migration_policy,
)


def test_decide_native_migration_uses_jit_first_policy() -> None:
    evidence = MigrationEvidence(
        module="orderbook_sequence",
        latency_ms_p95=75.0,
        throughput_per_sec=80.0,
        cpu_pct=85.0,
        jit_benchmark_gain_pct=10.0,
        mode="live",
    )
    decision = decide_native_migration(evidence)
    assert decision["bottleneck_detected"] is True
    assert decision["should_migrate_native"] is True


def test_build_native_release_matrix_contains_platform_rows() -> None:
    rows = build_native_release_matrix("pqts_hotpath")
    assert len(rows) >= 6
    assert any(row.target == "manylinux_x86_64" for row in rows)
    assert any(row.target == "macos_arm64" for row in rows)


def test_load_migration_policy_reads_thresholds(tmp_path: Path) -> None:
    policy_path = tmp_path / "migration_policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "thresholds": {"latency_ms_p95": 40.0, "cpu_pct": 70.0, "throughput_per_sec": 120.0},
                "kernel_classes": {"numeric_vectorizable": "jit_first", "stateful_streaming": "native_priority"},
                "priority_modules": ["orderbook_sequence"],
            }
        ),
        encoding="utf-8",
    )
    policy = load_migration_policy(policy_path)
    assert policy.thresholds.latency_ms_p95 == 40.0
    assert "orderbook_sequence" in policy.priority_modules
