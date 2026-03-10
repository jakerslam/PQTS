"""Tests for runtime performance profile resolution."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.performance_profile import resolve_runtime_performance_settings


def test_resolve_runtime_performance_settings_uses_low_latency_defaults():
    settings = resolve_runtime_performance_settings(
        {
            "performance": {
                "profile": "low_latency",
            }
        }
    )
    assert settings.profile == "low_latency"
    assert settings.loop_mode == "event_driven"
    assert settings.tick_interval_seconds == 0.05
    assert settings.poll_interval_seconds == 0.01
    assert settings.idle_sleep_seconds == 0.02
    assert settings.error_backoff_seconds == 0.50


def test_resolve_runtime_performance_settings_prefers_explicit_loop_over_profile():
    settings = resolve_runtime_performance_settings(
        {
            "performance": {
                "profile": "ultra_low_latency",
            },
            "loop": {
                "mode": "tick",
                "tick_interval_seconds": 0.2,
                "poll_interval_seconds": 0.1,
                "idle_sleep_seconds": 0.3,
                "error_backoff_seconds": 0.4,
            },
        }
    )
    assert settings.profile == "ultra_low_latency"
    assert settings.loop_mode == "tick"
    assert settings.tick_interval_seconds == 0.2
    assert settings.poll_interval_seconds == 0.1
    assert settings.idle_sleep_seconds == 0.3
    assert settings.error_backoff_seconds == 0.4
