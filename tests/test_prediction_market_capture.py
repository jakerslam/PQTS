from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from research.prediction_market_capture import (
    append_prediction_market_capture,
    load_prediction_market_capture_manifest,
    normalize_prediction_market_capture_payload,
)
from research.prediction_market_replay import load_prediction_market_snapshot_jsonl


def _load_capture_cli():
    script_path = Path("scripts/capture_prediction_market_snapshots.py").resolve()
    spec = importlib.util.spec_from_file_location("capture_prediction_market_snapshots", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normalize_capture_payload_accepts_common_book_aliases() -> None:
    snapshot = normalize_prediction_market_capture_payload(
        {
            "condition_id": "market-1",
            "token_id": "yes-token",
            "ts": "2026-05-30T12:00:00+00:00",
            "best_bid": "0.41",
            "best_ask": "0.43",
            "bid_size": "120",
            "ask_size": "95",
            "volume": "1000",
            "liquidity_num": "5000",
        },
        source="polymarket_ws",
    )

    assert snapshot.market_id == "market-1"
    assert snapshot.outcome_id == "yes-token"
    assert snapshot.yes_bid == 0.41
    assert snapshot.yes_ask == 0.43
    assert snapshot.source == "polymarket_ws"
    assert snapshot.metadata["capture_source"] == "polymarket_ws"


def test_append_prediction_market_capture_writes_manifest_and_appends(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.jsonl"
    manifest_path = tmp_path / "manifest.json"

    first = append_prediction_market_capture(
        [
            {
                "market_id": "m1",
                "outcome_id": "yes",
                "timestamp": "2026-05-30T12:00:00+00:00",
                "yes_bid": 0.50,
                "yes_ask": 0.52,
            }
        ],
        raw_snapshot_path=raw_path,
        source="fixture",
        manifest_path=manifest_path,
        append=False,
    )
    second = append_prediction_market_capture(
        [
            {
                "market_id": "m1",
                "outcome_id": "yes",
                "timestamp": "2026-05-30T12:00:01+00:00",
                "yes_bid": 0.51,
                "yes_ask": 0.53,
            }
        ],
        raw_snapshot_path=raw_path,
        source="fixture",
        manifest_path=manifest_path,
        append=True,
    )

    loaded = load_prediction_market_capture_manifest(manifest_path)
    snapshots = load_prediction_market_snapshot_jsonl(raw_path)
    assert first.row_count == 1
    assert second.row_count == 2
    assert loaded.row_count == 2
    assert loaded.manifest_id.startswith("pm_capture_")
    assert loaded.raw_sha256 == second.raw_sha256
    assert len(snapshots) == 2
    assert snapshots[1].yes_bid == 0.51


def test_capture_prediction_market_snapshots_cli_backfills_jsonl(tmp_path: Path, capsys) -> None:
    module = _load_capture_cli()
    input_path = tmp_path / "input.jsonl"
    raw_path = tmp_path / "captured.jsonl"
    manifest_path = tmp_path / "capture_manifest.json"
    input_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "market_id": "m1",
                        "outcome_id": "yes",
                        "timestamp": "2026-05-30T12:00:00+00:00",
                        "yes_bid": 0.40,
                        "yes_ask": 0.42,
                    },
                    sort_keys=True,
                ),
                json.dumps(
                    {
                        "market_id": "m2",
                        "outcome_id": "yes",
                        "timestamp": "2026-05-30T12:00:01+00:00",
                        "yes_bid": 0.60,
                        "yes_ask": 0.62,
                    },
                    sort_keys=True,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rc = module.main(
        [
            "--input-jsonl",
            str(input_path),
            "--out",
            str(raw_path),
            "--manifest-out",
            str(manifest_path),
            "--source",
            "fixture_feed",
            "--max-snapshots",
            "1",
            "--metadata",
            'venue="polymarket"',
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    snapshots = load_prediction_market_snapshot_jsonl(raw_path)
    assert rc == 0
    assert payload["ok"] is True
    assert payload["row_count"] == 1
    assert payload["metadata"]["venue"] == "polymarket"
    assert manifest_path.exists()
    assert len(snapshots) == 1
    assert snapshots[0].source == "fixture_feed"
