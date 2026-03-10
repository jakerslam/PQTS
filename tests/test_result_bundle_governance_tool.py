from __future__ import annotations

import json
from pathlib import Path

from tools.check_result_bundle_governance import (
    validate_and_build_reference_artifacts,
    write_reference_artifacts,
)


def _write_bundle(
    root: Path,
    *,
    name: str,
    market: str,
    strategy: str,
    quality: float,
    filled: int,
    submitted: int,
    reject_rate: float,
    dataset_version: str,
) -> Path:
    bundle = root / name
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "README.md").write_text("# Bundle\n\n## Command\n```bash\nrun\n```\n", encoding="utf-8")
    (bundle / "config_paper_snapshot.yaml").write_text("mode: paper_trading\n", encoding="utf-8")
    (bundle / "simulation_leaderboard_20260310T000000000000Z.csv").write_text(
        "market,strategy,runs,avg_quality_score,avg_fill_rate,avg_reject_rate\n"
        f"{market},{strategy},1,{quality},{(filled / max(1, submitted))},{reject_rate}\n",
        encoding="utf-8",
    )
    suite_payload = {
        "created_at": "2026-03-10T00:00:00+00:00",
        "results": [
            {
                "quality_score": quality,
                "filled": filled,
                "submitted": submitted,
                "reject_rate": reject_rate,
                "scenario": {
                    "market": market,
                    "strategy": strategy,
                    "notional_usd": 100.0,
                },
            }
        ],
    }
    (bundle / "simulation_suite_20260310T000000000000Z.json").write_text(
        json.dumps(suite_payload, sort_keys=True),
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "1",
        "dataset_version": dataset_version,
        "generated_at": "2026-03-10T00:00:00+00:00",
        "sources": [{"name": "simulated", "type": "synthetic"}],
    }
    (bundle / "dataset_manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    return bundle


def test_validate_and_build_reference_artifacts_success(tmp_path: Path) -> None:
    results = tmp_path / "results"
    results.mkdir()
    _write_bundle(
        results,
        name="2026-03-08_pack_a",
        market="crypto",
        strategy="market_making",
        quality=0.10,
        filled=6,
        submitted=10,
        reject_rate=0.40,
        dataset_version="dataset-2026-03-v1",
    )
    _write_bundle(
        results,
        name="2026-03-09_pack_b",
        market="crypto",
        strategy="market_making",
        quality=0.15,
        filled=7,
        submitted=10,
        reject_rate=0.30,
        dataset_version="dataset-2026-03-v1",
    )
    _write_bundle(
        results,
        name="2026-03-10_pack_c",
        market="equities",
        strategy="mean_reversion",
        quality=0.05,
        filled=5,
        submitted=10,
        reject_rate=0.50,
        dataset_version="dataset-2026-03-v1",
    )

    errors, index_rows, diffs = validate_and_build_reference_artifacts(
        results_dir=results,
        min_reference_packs=3,
    )

    assert errors == []
    assert len(index_rows) == 3
    assert len(diffs) == 1

    out = tmp_path / "out"
    index_path, diff_path = write_reference_artifacts(
        index_rows=index_rows,
        diffs=diffs,
        index_out=out / "index.json",
        diff_out=out / "diff.json",
    )
    assert index_path.exists()
    assert diff_path.exists()


def test_validate_and_build_reference_artifacts_missing_manifest(tmp_path: Path) -> None:
    results = tmp_path / "results"
    results.mkdir()
    bundle = _write_bundle(
        results,
        name="2026-03-10_pack_missing_manifest",
        market="crypto",
        strategy="market_making",
        quality=0.05,
        filled=1,
        submitted=10,
        reject_rate=0.90,
        dataset_version="dataset-2026-03-v1",
    )
    (bundle / "dataset_manifest.json").unlink()

    errors, _, _ = validate_and_build_reference_artifacts(
        results_dir=results,
        min_reference_packs=1,
    )
    assert any("missing required artifact 'dataset_manifest'" in item for item in errors)
