"""Tests for strategy plugin SDK discovery/scaffolding."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from strategies.plugin_sdk import discover_plugins, scaffold_strategy_plugin, strategy_slug


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
