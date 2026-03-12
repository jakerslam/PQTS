#!/usr/bin/env python3
"""Generate reproducible reference result bundles with non-zero fills."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REFERENCE_MIN_QUALITY = 0.25


@dataclass(frozen=True)
class ReferenceScenario:
    slug: str
    markets: str
    strategies: str
    cycles_per_scenario: int
    symbols_per_market: int
    readiness_every: int
    risk_profile: str = "balanced"


DEFAULT_SCENARIOS: tuple[ReferenceScenario, ...] = (
    ReferenceScenario(
        slug="reference_crypto_trend_following",
        markets="crypto",
        strategies="trend_following",
        cycles_per_scenario=36,
        symbols_per_market=1,
        readiness_every=12,
    ),
    ReferenceScenario(
        slug="reference_crypto_funding_arbitrage",
        markets="crypto",
        strategies="funding_arbitrage",
        cycles_per_scenario=36,
        symbols_per_market=1,
        readiness_every=12,
    ),
    ReferenceScenario(
        slug="reference_multi_market_making",
        markets="crypto,equities,forex",
        strategies="market_making",
        cycles_per_scenario=30,
        symbols_per_market=1,
        readiness_every=10,
    ),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _run(cmd: list[str]) -> dict[str, Any]:
    completed = subprocess.run(  # noqa: S603
        cmd,
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {' '.join(cmd)}\n"
            f"stdout={completed.stdout}\n"
            f"stderr={completed.stderr}"
        )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"No JSON payload from command: {' '.join(cmd)}")
    return json.loads(lines[-1])


def _quality_summary(payload: dict[str, Any]) -> dict[str, float]:
    rows = list(payload.get("results", []))
    if not rows:
        return {
            "total_submitted": 0.0,
            "total_filled": 0.0,
            "total_rejected": 0.0,
            "avg_quality_score": 0.0,
            "avg_fill_rate": 0.0,
            "avg_reject_rate": 0.0,
        }
    submitted = float(sum(float(row.get("submitted", 0.0)) for row in rows))
    filled = float(sum(float(row.get("filled", 0.0)) for row in rows))
    rejected = float(sum(float(row.get("rejected", 0.0)) for row in rows))
    avg_quality = float(sum(float(row.get("quality_score", 0.0)) for row in rows) / len(rows))
    avg_fill_rate = float(filled / max(submitted, 1.0))
    avg_reject_rate = float(rejected / max(submitted, 1.0))
    return {
        "total_submitted": submitted,
        "total_filled": filled,
        "total_rejected": rejected,
        "avg_quality_score": avg_quality,
        "avg_fill_rate": avg_fill_rate,
        "avg_reject_rate": avg_reject_rate,
    }


def _trust_label_from_summary(summary: dict[str, float]) -> str:
    quality = float(summary.get("avg_quality_score", 0.0) or 0.0)
    fill = float(summary.get("avg_fill_rate", 0.0) or 0.0)
    if quality >= REFERENCE_MIN_QUALITY and fill > 0.0:
        return "reference"
    if fill > 0.0:
        return "diagnostic_only"
    return "unverified"


def _render_metrics_chart(path: Path, *, quality: float, fill_rate: float, reject_rate: float) -> None:
    width = 720
    height = 320
    margin = 80
    bar_width = 120
    gap = 60
    values = [
        ("Quality", max(min(float(quality), 1.0), 0.0), "#1f77b4"),
        ("Fill", max(min(float(fill_rate), 1.0), 0.0), "#2ca02c"),
        ("Reject", max(min(float(reject_rate), 1.0), 0.0), "#d62728"),
    ]
    bars: list[str] = []
    labels: list[str] = []
    for idx, (label, value, color) in enumerate(values):
        x = margin + idx * (bar_width + gap)
        usable_h = height - 2 * margin
        h = usable_h * value
        y = height - margin - h
        bars.append(
            f'<rect x="{x}" y="{y:.1f}" width="{bar_width}" height="{h:.1f}" fill="{color}" rx="8" />'
        )
        labels.append(
            f'<text x="{x + bar_width/2:.1f}" y="{height - margin + 28}" text-anchor="middle" '
            f'font-family="Arial" font-size="16">{label}</text>'
        )
        labels.append(
            f'<text x="{x + bar_width/2:.1f}" y="{max(y - 10, 18):.1f}" text-anchor="middle" '
            f'font-family="Arial" font-size="15" fill="#111">{value:.2f}</text>'
        )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        'viewBox="0 0 720 320">\n'
        '<rect width="100%" height="100%" fill="#ffffff"/>\n'
        '<text x="360" y="38" text-anchor="middle" font-family="Arial" font-size="20" '
        'fill="#111">Reference Bundle Metrics</text>\n'
        '<line x1="70" y1="240" x2="660" y2="240" stroke="#888" stroke-width="1.2"/>\n'
        + "\n".join(bars + labels)
        + "\n</svg>\n"
    )
    path.write_text(svg, encoding="utf-8")


def _write_bundle_readme(
    path: Path,
    *,
    bundle_name: str,
    scenario: ReferenceScenario,
    command: str,
    payload: dict[str, Any],
    summary: dict[str, float],
) -> None:
    rows = payload.get("results", [])
    per_scenario = "\n".join(
        "- `{market}/{strategy}`: quality={quality_score:.2f}, fill={fill:.2f}, reject={reject:.2f}, submitted={submitted:.0f}".format(
            market=str(row.get("scenario", {}).get("market", "n/a")),
            strategy=str(row.get("scenario", {}).get("strategy", "n/a")),
            quality_score=float(row.get("quality_score", 0.0)),
            fill=(float(row.get("filled", 0.0)) / max(float(row.get("submitted", 0.0)), 1.0)),
            reject=(float(row.get("rejected", 0.0)) / max(float(row.get("submitted", 0.0)), 1.0)),
            submitted=float(row.get("submitted", 0.0)),
        )
        for row in rows
    )
    text = f"""# Result Bundle: {bundle_name}

## Run Metadata

- Date (UTC): {datetime.now(timezone.utc).isoformat()}
- Risk profile: {scenario.risk_profile}
- Scenario count: {int(payload.get("scenario_count", 0))}
- Config snapshot: `config_paper_snapshot.yaml`

## Command

```bash
{command}
```

## Included Artifacts

- `{Path(str(payload.get("report_path", ""))).name}`
- `{Path(str(payload.get("leaderboard_path", ""))).name}`
- `metrics_chart.svg`
- `config_paper_snapshot.yaml`
- `dataset_manifest.json`

## Key Metrics

- total_submitted={summary["total_submitted"]:.0f}
- total_filled={summary["total_filled"]:.0f}
- total_rejected={summary["total_rejected"]:.0f}
- avg_quality_score={summary["avg_quality_score"]:.4f}
- avg_fill_rate={summary["avg_fill_rate"]:.4f}
- avg_reject_rate={summary["avg_reject_rate"]:.4f}

{per_scenario}

## Claim Classification

- Claim class: `reference`
- Evidence source: `{Path(str(payload.get("report_path", ""))).name}` + `{Path(str(payload.get("leaderboard_path", ""))).name}`
- Non-zero fill gate: `passed`

## Notes

Reference-quality bundle intended for public reproducibility and benchmark governance.
"""
    path.write_text(text, encoding="utf-8")


def _write_dataset_manifest(path: Path, *, payload: dict[str, Any], command: str) -> None:
    report_path = Path(str(payload.get("report_path", "")))
    leaderboard_path = Path(str(payload.get("leaderboard_path", "")))
    manifest = {
        "schema_version": "1",
        "dataset_version": f"dataset-{datetime.now(timezone.utc).strftime('%Y%m%d')}-reference-v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": [
            {
                "name": "pqts_simulation_engine",
                "type": "synthetic",
                "config": str(payload.get("config_path", "config/paper.yaml")),
            }
        ],
        "commands": [command],
        "artifacts": {
            "report_json": report_path.name,
            "report_sha256": _sha256(report_path) if report_path.exists() else "",
            "leaderboard_csv": leaderboard_path.name,
            "leaderboard_sha256": _sha256(leaderboard_path) if leaderboard_path.exists() else "",
        },
        "notes": "Reference bundle with non-zero fills and reproducible command surface.",
    }
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def publish_bundles(*, config: str, out_root: Path, scenarios: tuple[ReferenceScenario, ...]) -> dict[str, Any]:
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    generated_at = datetime.now(timezone.utc).isoformat()
    generated: list[dict[str, Any]] = []
    for scenario in scenarios:
        bundle_name = f"{date_prefix}_{scenario.slug}"
        bundle = out_root / bundle_name
        bundle.mkdir(parents=True, exist_ok=True)
        command = [
            sys.executable,
            str(ROOT / "scripts" / "run_simulation_suite.py"),
            "--config",
            str(config),
            "--markets",
            scenario.markets,
            "--strategies",
            scenario.strategies,
            "--cycles-per-scenario",
            str(scenario.cycles_per_scenario),
            "--symbols-per-market",
            str(scenario.symbols_per_market),
            "--readiness-every",
            str(scenario.readiness_every),
            "--risk-profile",
            scenario.risk_profile,
            "--sleep-seconds",
            "0.0",
            "--out-dir",
            str(bundle),
            "--telemetry-log",
            str(bundle / "simulation_events.jsonl"),
            "--tca-dir",
            str(bundle / "tca"),
        ]
        payload = _run(command)
        summary = _quality_summary(payload)
        trust_label = _trust_label_from_summary(summary)
        if summary["total_filled"] <= 0:
            raise RuntimeError(
                f"Reference bundle {bundle_name} has zero fills; refusing to publish as reference."
            )
        if trust_label != "reference":
            raise RuntimeError(
                f"Reference bundle {bundle_name} classified as {trust_label}; "
                f"requires quality>={REFERENCE_MIN_QUALITY} and non-zero fills."
            )

        config_snapshot = bundle / "config_paper_snapshot.yaml"
        shutil.copy2(str(ROOT / config), str(config_snapshot))

        _write_dataset_manifest(
            bundle / "dataset_manifest.json",
            payload=payload,
            command=" ".join(command).replace(str(ROOT) + "/", ""),
        )
        _render_metrics_chart(
            bundle / "metrics_chart.svg",
            quality=summary["avg_quality_score"],
            fill_rate=summary["avg_fill_rate"],
            reject_rate=summary["avg_reject_rate"],
        )
        _write_bundle_readme(
            bundle / "README.md",
            bundle_name=bundle_name,
            scenario=scenario,
            command=" ".join(command).replace(str(ROOT) + "/", ""),
            payload=payload,
            summary=summary,
        )
        generated.append(
            {
                "bundle": bundle_name,
                "path": str(bundle),
                "summary": summary,
                "report_path": str(payload.get("report_path", "")),
                "leaderboard_path": str(payload.get("leaderboard_path", "")),
                "markets": scenario.markets,
                "strategies": scenario.strategies,
                "command": " ".join(command).replace(str(ROOT) + "/", ""),
                "trust_label": trust_label,
                "provenance": {
                    "generated_at": generated_at,
                    "generator": "scripts/publish_reference_bundles.py",
                    "dataset_manifest_path": str(bundle / "dataset_manifest.json"),
                    "config_snapshot_path": str(bundle / "config_paper_snapshot.yaml"),
                    "metrics_chart_path": str(bundle / "metrics_chart.svg"),
                },
            }
        )

    output = {
        "schema_version": "2",
        "generated_at": generated_at,
        "bundle_count": len(generated),
        "trust_label": "reference",
        "provenance": {
            "generated_at": generated_at,
            "generator": "scripts/publish_reference_bundles.py",
            "source_policy": "docs/BENCHMARKS.md",
            "artifact_path": str(out_root / "reference_performance_latest.json"),
            "bundle_count": len(generated),
        },
        "bundles": generated,
    }
    summary_path = out_root / "reference_performance_latest.json"
    summary_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/paper.yaml")
    parser.add_argument("--out-root", default="results")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    payload = publish_bundles(
        config=str(args.config),
        out_root=Path(args.out_root),
        scenarios=DEFAULT_SCENARIOS,
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
