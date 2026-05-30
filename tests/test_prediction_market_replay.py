from __future__ import annotations

import json
from datetime import datetime, timezone

from research.prediction_market_microstructure import PredictionMarketBookSnapshot
from research.prediction_market_replay import (
    SCHEMA_VERSION,
    build_prediction_market_feature_artifact,
    load_prediction_market_replay_manifest,
    load_prediction_market_snapshot_jsonl,
    write_prediction_market_snapshot_jsonl,
)


def _ts(second: int) -> datetime:
    return datetime(2026, 1, 1, 12, 0, second, tzinfo=timezone.utc)


def _snapshots() -> list[PredictionMarketBookSnapshot]:
    return [
        PredictionMarketBookSnapshot(
            market_id="mkt_1",
            outcome_id="yes",
            timestamp=_ts(0),
            yes_bid=0.44,
            yes_ask=0.46,
            yes_bid_size=120.0,
            yes_ask_size=80.0,
            no_bid=0.53,
            no_ask=0.55,
            traded_volume=1000.0,
            liquidity=5000.0,
            source="polymarket_ws",
            sequence=1,
            resolved_probability=1.0,
        ),
        PredictionMarketBookSnapshot(
            market_id="mkt_1",
            outcome_id="yes",
            timestamp=_ts(10),
            yes_bid=0.47,
            yes_ask=0.49,
            yes_bid_size=140.0,
            yes_ask_size=60.0,
            no_bid=0.50,
            no_ask=0.52,
            traded_volume=1030.0,
            liquidity=5100.0,
            source="polymarket_ws",
            sequence=2,
            resolved_probability=1.0,
        ),
    ]


def test_prediction_market_snapshot_jsonl_roundtrip(tmp_path) -> None:
    raw_path = write_prediction_market_snapshot_jsonl(_snapshots(), tmp_path / "raw.jsonl")

    loaded = load_prediction_market_snapshot_jsonl(raw_path)

    assert len(loaded) == 2
    assert loaded[0].market_id == "mkt_1"
    assert loaded[0].timestamp == _ts(0)


def test_prediction_market_replay_manifest_builds_reproducible_feature_artifact(tmp_path) -> None:
    raw_path = write_prediction_market_snapshot_jsonl(_snapshots(), tmp_path / "raw.jsonl")
    feature_path = tmp_path / "features.jsonl"
    manifest_path = tmp_path / "manifest.json"

    manifest = build_prediction_market_feature_artifact(
        raw_snapshot_path=raw_path,
        feature_snapshot_path=feature_path,
        manifest_path=manifest_path,
        source="polymarket_ws",
        metadata={"dataset": "unit"},
    )

    assert manifest.schema_version == SCHEMA_VERSION
    assert manifest.row_count == 2
    assert manifest.market_count == 1
    assert manifest.outcome_count == 1
    assert manifest.raw_sha256
    assert manifest.feature_sha256
    assert "yes_mid_probability" in manifest.feature_columns
    assert "resolved_probability" not in manifest.feature_columns
    assert manifest.metadata["dataset"] == "unit"

    rows = [json.loads(line) for line in feature_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert "resolved_probability" not in rows[0]

    loaded = load_prediction_market_replay_manifest(manifest_path)
    assert loaded.manifest_id == manifest.manifest_id
    assert loaded.feature_sha256 == manifest.feature_sha256


def test_prediction_market_replay_manifest_is_stable_for_same_inputs(tmp_path) -> None:
    raw_path = write_prediction_market_snapshot_jsonl(_snapshots(), tmp_path / "raw.jsonl")

    first = build_prediction_market_feature_artifact(
        raw_snapshot_path=raw_path,
        feature_snapshot_path=tmp_path / "features_a.jsonl",
        manifest_path=tmp_path / "manifest_a.json",
        source="polymarket_ws",
    )
    second = build_prediction_market_feature_artifact(
        raw_snapshot_path=raw_path,
        feature_snapshot_path=tmp_path / "features_b.jsonl",
        manifest_path=tmp_path / "manifest_b.json",
        source="polymarket_ws",
    )

    assert first.manifest_id == second.manifest_id
    assert first.feature_sha256 == second.feature_sha256
