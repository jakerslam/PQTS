"""Native hot-path migration trigger and release-matrix contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class MigrationEvidence:
    module: str
    latency_ms_p95: float
    throughput_per_sec: float
    cpu_pct: float
    jit_benchmark_gain_pct: float
    mode: str


@dataclass(frozen=True)
class MigrationThresholds:
    latency_ms_p95: float = 50.0
    cpu_pct: float = 80.0
    throughput_per_sec: float = 100.0
    min_jit_gain_pct: float = 20.0


@dataclass(frozen=True)
class MigrationPolicy:
    thresholds: MigrationThresholds
    numeric_vectorizable_mode: str = "jit_first"
    stateful_streaming_mode: str = "native_priority"
    priority_modules: tuple[str, ...] = ()


@dataclass(frozen=True)
class NativeReleaseArtifact:
    target: str
    python_version: str
    wheel_tag: str
    native_module: str


def load_migration_policy(path: str | Path = "config/native/migration_policy.json") -> MigrationPolicy:
    policy_path = Path(path)
    if not policy_path.exists():
        return MigrationPolicy(thresholds=MigrationThresholds())

    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    thresholds = payload.get("thresholds", {})
    kernel_classes = payload.get("kernel_classes", {})

    return MigrationPolicy(
        thresholds=MigrationThresholds(
            latency_ms_p95=float(thresholds.get("latency_ms_p95", 50.0)),
            cpu_pct=float(thresholds.get("cpu_pct", 80.0)),
            throughput_per_sec=float(thresholds.get("throughput_per_sec", 100.0)),
            min_jit_gain_pct=float(thresholds.get("min_jit_gain_pct", 20.0)),
        ),
        numeric_vectorizable_mode=str(kernel_classes.get("numeric_vectorizable", "jit_first")),
        stateful_streaming_mode=str(kernel_classes.get("stateful_streaming", "native_priority")),
        priority_modules=tuple(str(token) for token in payload.get("priority_modules", []) if str(token).strip()),
    )


def decide_native_migration(
    evidence: MigrationEvidence,
    *,
    policy: MigrationPolicy | None = None,
    kernel_class: str = "stateful_streaming",
) -> dict[str, Any]:
    resolved = policy or MigrationPolicy(thresholds=MigrationThresholds())
    thresholds = resolved.thresholds

    bottleneck = (
        evidence.latency_ms_p95 > float(thresholds.latency_ms_p95)
        or evidence.cpu_pct > float(thresholds.cpu_pct)
        or evidence.throughput_per_sec < float(thresholds.throughput_per_sec)
    )
    jit_sufficient = evidence.jit_benchmark_gain_pct >= float(thresholds.min_jit_gain_pct)

    klass = str(kernel_class).strip().lower() or "stateful_streaming"
    is_priority_module = str(evidence.module).strip() in set(resolved.priority_modules)

    should_migrate = False
    if klass == "numeric_vectorizable":
        should_migrate = bottleneck and (not jit_sufficient)
    else:
        native_priority = str(resolved.stateful_streaming_mode).strip().lower() == "native_priority"
        should_migrate = bottleneck and ((not jit_sufficient) or (native_priority and is_priority_module))

    return {
        "module": evidence.module,
        "kernel_class": klass,
        "bottleneck_detected": bool(bottleneck),
        "jit_sufficient": bool(jit_sufficient),
        "is_priority_module": bool(is_priority_module),
        "should_migrate_native": bool(should_migrate),
        "mode": evidence.mode,
        "thresholds": {
            "latency_ms_p95": float(thresholds.latency_ms_p95),
            "cpu_pct": float(thresholds.cpu_pct),
            "throughput_per_sec": float(thresholds.throughput_per_sec),
            "min_jit_gain_pct": float(thresholds.min_jit_gain_pct),
        },
    }


def build_native_release_matrix(native_module: str) -> list[NativeReleaseArtifact]:
    targets = [
        ("manylinux_x86_64", "cp311", "cp311-manylinux_x86_64"),
        ("manylinux_x86_64", "cp312", "cp312-manylinux_x86_64"),
        ("macos_arm64", "cp311", "cp311-macosx_11_0_arm64"),
        ("macos_arm64", "cp312", "cp312-macosx_11_0_arm64"),
        ("windows_amd64", "cp311", "cp311-win_amd64"),
        ("windows_amd64", "cp312", "cp312-win_amd64"),
    ]
    return [
        NativeReleaseArtifact(
            target=target,
            python_version=py,
            wheel_tag=wheel,
            native_module=native_module,
        )
        for target, py, wheel in targets
    ]
