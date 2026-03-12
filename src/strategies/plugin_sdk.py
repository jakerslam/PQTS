"""Strategy plugin SDK for extension discovery and scaffolding."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Iterable


_SLUG_RE = re.compile(r"[^a-z0-9_]+")


def strategy_slug(name: str) -> str:
    slug = _SLUG_RE.sub("_", str(name).strip().lower()).strip("_")
    return slug or "custom_strategy"


@dataclass(frozen=True)
class StrategyPluginMetadata:
    plugin_id: str
    name: str
    module: str
    class_name: str
    version: str
    description: str
    markets: tuple[str, ...]
    risk_profile: str

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "StrategyPluginMetadata":
        return cls(
            plugin_id=str(payload.get("plugin_id", "")),
            name=str(payload.get("name", "")),
            module=str(payload.get("module", "")),
            class_name=str(payload.get("class_name", "")),
            version=str(payload.get("version", "0.1.0")),
            description=str(payload.get("description", "")),
            markets=tuple(str(item) for item in payload.get("markets", []) if str(item).strip()),
            risk_profile=str(payload.get("risk_profile", "balanced")),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "module": self.module,
            "class_name": self.class_name,
            "version": self.version,
            "description": self.description,
            "markets": list(self.markets),
            "risk_profile": self.risk_profile,
        }


def discover_plugins(root: str | Path = "plugins/strategies") -> list[StrategyPluginMetadata]:
    plugins_root = Path(root)
    if not plugins_root.exists():
        return []
    rows: list[StrategyPluginMetadata] = []
    for manifest in sorted(plugins_root.glob("*/plugin.json")):
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            rows.append(StrategyPluginMetadata.from_dict(payload))
    return rows


def validate_plugin_manifest(payload: dict[str, object]) -> dict[str, object]:
    required = ["plugin_id", "name", "module", "class_name", "version", "markets", "risk_profile"]
    missing = [field for field in required if field not in payload]
    markets = payload.get("markets", [])
    markets_ok = isinstance(markets, list) and all(str(item).strip() for item in markets)
    plugin_id = str(payload.get("plugin_id", "")).strip()
    module = str(payload.get("module", "")).strip()
    class_name = str(payload.get("class_name", "")).strip()
    trust_label = str(payload.get("trust_label", "unverified")).strip().lower()
    gate_verified = bool(payload.get("gate_verified", False))
    errors: list[str] = []
    if missing:
        errors.append(f"missing fields: {', '.join(missing)}")
    if not plugin_id:
        errors.append("plugin_id must be non-empty")
    if not module:
        errors.append("module must be non-empty")
    if not class_name:
        errors.append("class_name must be non-empty")
    if not markets_ok:
        errors.append("markets must be a non-empty list of tokens")
    if gate_verified and trust_label != "reference":
        errors.append("gate_verified plugins require trust_label=reference")
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "gate_verified": gate_verified,
        "trust_label": trust_label or "unverified",
    }


def scaffold_strategy_plugin(
    *,
    name: str,
    out_root: str | Path = "plugins/strategies",
    template: str = "basic",
    force: bool = False,
) -> dict[str, str]:
    slug = strategy_slug(name)
    class_name = "".join(token.capitalize() for token in slug.split("_")) + "Strategy"
    plugin_dir = Path(out_root) / slug
    if plugin_dir.exists() and not force:
        raise FileExistsError(f"Plugin directory already exists: {plugin_dir}")
    plugin_dir.mkdir(parents=True, exist_ok=True)

    init_path = plugin_dir / "__init__.py"
    strategy_path = plugin_dir / "strategy.py"
    manifest_path = plugin_dir / "plugin.json"
    readme_path = plugin_dir / "README.md"

    init_path.write_text(
        f'"""Strategy plugin package: {slug}."""\n\n'
        f"from .strategy import {class_name}\n\n"
        f'__all__ = ["{class_name}"]\n',
        encoding="utf-8",
    )

    strategy_template = _strategy_template(
        class_name=class_name,
        plugin_id=slug,
        template=template,
    )
    strategy_path.write_text(strategy_template, encoding="utf-8")

    metadata = StrategyPluginMetadata(
        plugin_id=slug,
        name=str(name).strip() or slug,
        module=f"plugins.strategies.{slug}.strategy",
        class_name=class_name,
        version="0.1.0",
        description=f"{name} strategy plugin scaffold",
        markets=("crypto",),
        risk_profile="balanced",
    )
    manifest_path.write_text(json.dumps(metadata.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    readme_path.write_text(
        (
            f"# Strategy Plugin: {metadata.name}\n\n"
            "Generated by `pqts new-strategy`.\n\n"
            "## Quick Start\n\n"
            "1. Implement `generate_signals` in `strategy.py`.\n"
            "2. Update `plugin.json` markets/risk profile metadata.\n"
            "3. Add plugin-specific unit tests under `tests/plugins/`.\n"
        ),
        encoding="utf-8",
    )

    return {
        "plugin_id": slug,
        "plugin_dir": str(plugin_dir),
        "manifest": str(manifest_path),
        "strategy_module": str(strategy_path),
        "readme": str(readme_path),
    }


def _strategy_template(*, class_name: str, plugin_id: str, template: str) -> str:
    doc = f'{class_name} plugin strategy scaffold (template={template}).'
    return (
        f'"""{doc}"""\n\n'
        "from __future__ import annotations\n\n"
        "from dataclasses import dataclass\n"
        "from typing import Any\n\n\n"
        "@dataclass\n"
        f"class {class_name}:\n"
        f"    plugin_id: str = \"{plugin_id}\"\n"
        "    risk_profile: str = \"balanced\"\n\n"
        "    def generate_signals(self, market_snapshot: dict[str, Any]) -> list[dict[str, Any]]:\n"
        "        \"\"\"Return normalized signal payloads for router submission.\n\n"
        "        Replace this with strategy-specific logic.\n"
        "        \"\"\"\n"
        "        _ = market_snapshot\n"
        "        return []\n"
    )


def plugin_ids(root: str | Path = "plugins/strategies") -> Iterable[str]:
    for row in discover_plugins(root):
        yield row.plugin_id
