from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

from research.prediction_market_microstructure import PredictionMarketBookSnapshot
from research.prediction_market_replay import write_prediction_market_snapshot_jsonl

ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "scripts" / "build_prediction_market_replay.py"
SPEC = importlib.util.spec_from_file_location("build_prediction_market_replay", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _ts(second: int) -> datetime:
    return datetime(2026, 1, 1, 12, 0, second, tzinfo=timezone.utc)


def test_build_prediction_market_replay_cli_writes_manifest_and_features(tmp_path, capsys):
    raw_path = write_prediction_market_snapshot_jsonl(
        [
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
            )
        ],
        tmp_path / "raw.jsonl",
    )
    features_path = tmp_path / "features.jsonl"
    manifest_path = tmp_path / "manifest.json"

    exit_code = MODULE.main(
        [
            "--raw-snapshots",
            str(raw_path),
            "--features-out",
            str(features_path),
            "--manifest-out",
            str(manifest_path),
            "--source",
            "polymarket_ws",
            "--metadata",
            "dataset=unit",
            "--metadata",
            "version=1",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True
    assert output["row_count"] == 1
    assert output["metadata"]["dataset"] == "unit"
    assert output["metadata"]["version"] == 1
    assert features_path.exists()
    assert manifest_path.exists()
    feature_row = json.loads(features_path.read_text(encoding="utf-8").splitlines()[0])
    assert "resolved_probability" not in feature_row


def test_build_prediction_market_replay_cli_fails_quality_gate(tmp_path, capsys):
    raw_path = write_prediction_market_snapshot_jsonl(
        [
            {
                "market_id": "mkt_bad",
                "outcome_id": "yes",
                "timestamp": _ts(0).isoformat(),
                "yes_bid": 0.6,
                "yes_ask": 0.5,
                "yes_bid_size": 1.0,
                "yes_ask_size": 1.0,
                "traded_volume": 10.0,
                "liquidity": 10.0,
            }
        ],
        tmp_path / "raw_bad.jsonl",
    )

    exit_code = MODULE.main(
        [
            "--raw-snapshots",
            str(raw_path),
            "--features-out",
            str(tmp_path / "features_bad.jsonl"),
            "--manifest-out",
            str(tmp_path / "manifest_bad.json"),
            "--source",
            "polymarket_ws",
            "--fail-on-quality-flags",
        ]
    )

    assert exit_code == 2
    output = json.loads(capsys.readouterr().out)
    assert "quality_flags_present" in output["gate_failures"]
    assert output["quality_flag_counts"]["invalid_yes_quote"] == 1


def test_build_prediction_market_replay_cli_rejects_bad_metadata(tmp_path, capsys):
    raw_path = write_prediction_market_snapshot_jsonl([], tmp_path / "raw_empty.jsonl")

    exit_code = MODULE.main(
        [
            "--raw-snapshots",
            str(raw_path),
            "--features-out",
            str(tmp_path / "features.jsonl"),
            "--manifest-out",
            str(tmp_path / "manifest.json"),
            "--source",
            "polymarket_ws",
            "--metadata",
            "bad",
        ]
    )

    assert exit_code == 1
    error = json.loads(capsys.readouterr().err)
    assert error["ok"] is False
    assert "metadata must be KEY=VALUE" in error["error"]
