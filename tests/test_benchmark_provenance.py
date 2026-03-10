from __future__ import annotations

import json
from pathlib import Path

from analytics.benchmark_provenance import (
    build_benchmark_provenance_record,
    merge_and_write_benchmark_provenance_log,
    update_monthly_benchmark_provenance_log,
)


def _bundle_with_suite(root: Path, name: str, created_at: str) -> Path:
    bundle = root / name
    bundle.mkdir(parents=True, exist_ok=True)
    suite_payload = {
        "created_at": created_at,
        "config_path": "config/paper.yaml",
        "leaderboard": [
            {
                "market": "crypto",
                "strategy": "market_making",
                "runs": 1,
                "avg_quality_score": 0.1,
                "avg_fill_rate": 0.4,
                "avg_reject_rate": 0.6,
            }
        ],
        "results": [
            {
                "quality_score": 0.1,
                "filled": 4,
                "submitted": 10,
                "reject_rate": 0.6,
                "scenario": {"market": "crypto", "strategy": "market_making", "notional_usd": 100.0},
            }
        ],
        "leaderboard_path": str(bundle / "simulation_leaderboard_20260309T000000000000Z.csv"),
    }
    (bundle / "simulation_suite_20260309T000000000000Z.json").write_text(
        json.dumps(suite_payload), encoding="utf-8"
    )
    (bundle / "simulation_leaderboard_20260309T000000000000Z.csv").write_text(
        "market,strategy,runs\ncrypto,market_making,1\n", encoding="utf-8"
    )
    (bundle / "config_paper_snapshot.yaml").write_text("mode: paper_trading\n", encoding="utf-8")
    return bundle


def _seed_dataset_manifest(bundle: Path, dataset_version: str) -> None:
    payload = {
        "schema_version": "1",
        "dataset_version": dataset_version,
        "generated_at": "2026-03-09T00:00:00+00:00",
        "sources": [{"name": "sim", "type": "synthetic"}],
    }
    (bundle / "dataset_manifest.json").write_text(json.dumps(payload), encoding="utf-8")


def test_build_benchmark_provenance_record_has_required_fields(tmp_path: Path) -> None:
    bundle = _bundle_with_suite(tmp_path, "2026-03-09_bundle_a", "2026-03-09T00:00:00+00:00")
    _seed_dataset_manifest(bundle, "dataset-2026-03-v1")

    record = build_benchmark_provenance_record(
        bundle_dir=bundle,
        strategy_version="abc123",
        dataset_version="dataset-2026-03",
    )

    assert record is not None
    assert record.strategy_version == "abc123"
    assert record.dataset_version == "dataset-2026-03"
    assert record.run_timestamp == "2026-03-09T00:00:00+00:00"
    assert record.environment_hash
    assert record.scenario_count == 1
    assert "simulation_suite_20260309T000000000000Z.json" in record.artifact_hashes
    assert "dataset_manifest.json" in record.artifact_hashes


def test_build_benchmark_provenance_record_uses_manifest_version_when_no_override(tmp_path: Path) -> None:
    bundle = _bundle_with_suite(tmp_path, "2026-03-09_bundle_a", "2026-03-09T00:00:00+00:00")
    _seed_dataset_manifest(bundle, "dataset-2026-03-v2")

    record = build_benchmark_provenance_record(
        bundle_dir=bundle,
        strategy_version="abc123",
        dataset_version=None,
    )

    assert record is not None
    assert record.dataset_version == "dataset-2026-03-v2"


def test_merge_and_write_benchmark_provenance_log_deduplicates(tmp_path: Path) -> None:
    bundle = _bundle_with_suite(tmp_path, "2026-03-09_bundle_a", "2026-03-09T00:00:00+00:00")
    record = build_benchmark_provenance_record(
        bundle_dir=bundle,
        strategy_version="abc123",
        dataset_version="dataset-2026-03",
    )
    assert record is not None

    out = tmp_path / "benchmark_provenance.jsonl"
    merge_and_write_benchmark_provenance_log(records=[record], output_path=out)
    merge_and_write_benchmark_provenance_log(records=[record], output_path=out)

    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["bundle_name"] == "2026-03-09_bundle_a"


def test_update_monthly_benchmark_provenance_log_filters_month(tmp_path: Path) -> None:
    results = tmp_path / "results"
    results.mkdir()
    _bundle_with_suite(results, "2026-03-09_bundle_a", "2026-03-09T00:00:00+00:00")
    _bundle_with_suite(results, "2026-02-28_bundle_old", "2026-02-28T00:00:00+00:00")

    out = tmp_path / "logs" / "benchmark_provenance.jsonl"
    log_path = update_monthly_benchmark_provenance_log(
        results_dir=results,
        month="2026-03",
        output_path=out,
        repo_root=tmp_path,
        dataset_version="dataset-2026-03",
    )

    assert log_path == out
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["bundle_name"] == "2026-03-09_bundle_a"
    assert rows[0]["dataset_version"] == "dataset-2026-03"
    assert rows[0]["strategy_version"]
