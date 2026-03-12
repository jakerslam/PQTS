"""Tests for strategy plugin SDK discovery/scaffolding."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from strategies.plugin_sdk import (
    discover_plugins,
    scaffold_strategy_plugin,
    strategy_slug,
    validate_plugin_manifest,
)


def test_strategy_slug_normalizes_name() -> None:
    assert strategy_slug("My Alpha Strategy!") == "my_alpha_strategy"


def test_scaffold_strategy_plugin_creates_manifest_and_discoverable_plugin(tmp_path: Path) -> None:
    payload = scaffold_strategy_plugin(
        name="Momentum Burst",
        out_root=tmp_path / "plugins" / "strategies",
    )
    assert Path(payload["plugin_dir"]).exists()
    rows = discover_plugins(tmp_path / "plugins" / "strategies")
    assert len(rows) == 1
    assert rows[0].plugin_id == "momentum_burst"


def test_validate_plugin_manifest_enforces_reference_for_gate_verified() -> None:
    invalid = validate_plugin_manifest(
        {
            "plugin_id": "foo",
            "name": "Foo",
            "module": "plugins.foo",
            "class_name": "FooStrategy",
            "version": "0.1.0",
            "markets": ["crypto"],
            "risk_profile": "balanced",
            "gate_verified": True,
            "trust_label": "diagnostic_only",
        }
    )
    assert invalid["valid"] is False
    assert any("trust_label=reference" in reason for reason in invalid["errors"])

    valid = validate_plugin_manifest(
        {
            "plugin_id": "foo",
            "name": "Foo",
            "module": "plugins.foo",
            "class_name": "FooStrategy",
            "version": "0.1.0",
            "markets": ["crypto"],
            "risk_profile": "balanced",
            "gate_verified": True,
            "trust_label": "reference",
        }
    )
    assert valid["valid"] is True
