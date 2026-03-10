"""Runtime performance-profile resolution for execution loop settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class RuntimePerformanceSettings:
    """Resolved runtime settings for loop behavior and native requirements."""

    profile: str
    require_native_hotpath: bool
    loop_mode: str
    tick_interval_seconds: float
    poll_interval_seconds: float
    idle_sleep_seconds: float
    error_backoff_seconds: float


_PROFILE_DEFAULTS: dict[str, dict[str, float | str]] = {
    "balanced": {
        "loop_mode": "event_driven",
        "tick_interval_seconds": 1.0,
        "poll_interval_seconds": 0.05,
        "idle_sleep_seconds": 0.10,
        "error_backoff_seconds": 5.0,
    },
    "low_latency": {
        "loop_mode": "event_driven",
        "tick_interval_seconds": 0.05,
        "poll_interval_seconds": 0.01,
        "idle_sleep_seconds": 0.02,
        "error_backoff_seconds": 0.50,
    },
    "ultra_low_latency": {
        "loop_mode": "event_driven",
        "tick_interval_seconds": 0.02,
        "poll_interval_seconds": 0.005,
        "idle_sleep_seconds": 0.01,
        "error_backoff_seconds": 0.25,
    },
}

ALLOWED_PERFORMANCE_PROFILES: tuple[str, ...] = tuple(sorted(_PROFILE_DEFAULTS.keys()))


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def resolve_runtime_performance_settings(
    runtime_cfg: Mapping[str, Any] | None,
) -> RuntimePerformanceSettings:
    """Resolve profile defaults and explicit overrides into one runtime contract."""
    cfg = _mapping(runtime_cfg)
    performance_cfg = _mapping(cfg.get("performance"))
    profile = str(performance_cfg.get("profile", "balanced")).strip().lower() or "balanced"
    if profile not in _PROFILE_DEFAULTS:
        profile = "balanced"

    profile_defaults = _PROFILE_DEFAULTS[profile]
    loop_cfg = _mapping(cfg.get("loop"))

    loop_mode = str(
        loop_cfg.get("mode", cfg.get("loop_mode", profile_defaults["loop_mode"]))
    ).strip().lower()
    if loop_mode not in {"event_driven", "tick"}:
        loop_mode = "event_driven"

    return RuntimePerformanceSettings(
        profile=profile,
        require_native_hotpath=bool(performance_cfg.get("require_native_hotpath", False)),
        loop_mode=loop_mode,
        tick_interval_seconds=max(
            float(
                loop_cfg.get(
                    "tick_interval_seconds",
                    cfg.get("tick_interval_seconds", profile_defaults["tick_interval_seconds"]),
                )
            ),
            0.001,
        ),
        poll_interval_seconds=max(
            float(
                loop_cfg.get(
                    "poll_interval_seconds",
                    cfg.get("poll_interval_seconds", profile_defaults["poll_interval_seconds"]),
                )
            ),
            0.001,
        ),
        idle_sleep_seconds=max(
            float(
                loop_cfg.get(
                    "idle_sleep_seconds",
                    cfg.get("idle_sleep_seconds", profile_defaults["idle_sleep_seconds"]),
                )
            ),
            0.001,
        ),
        error_backoff_seconds=max(
            float(
                loop_cfg.get(
                    "error_backoff_seconds",
                    cfg.get("error_backoff_seconds", profile_defaults["error_backoff_seconds"]),
                )
            ),
            0.001,
        ),
    )
