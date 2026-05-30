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


def test_normalize_capture_payload_accepts_polymarket_clob_book() -> None:
    snapshot = normalize_prediction_market_capture_payload(
        {
            "market": "0xabc",
            "asset_id": "token-yes",
            "timestamp": "1780172484142",
            "hash": "book_hash",
            "bids": [
                {"price": "0.40", "size": "10"},
                {"price": "0.44", "size": "25"},
            ],
            "asks": [
                {"price": "0.50", "size": "20"},
                {"price": "0.48", "size": "15"},
            ],
            "min_order_size": "5",
            "tick_size": "0.01",
        },
        source="polymarket_clob",
    )

    assert snapshot.market_id == "0xabc"
    assert snapshot.outcome_id == "token-yes"
    assert snapshot.yes_bid == 0.44
    assert snapshot.yes_ask == 0.48
    assert snapshot.yes_bid_size == 25.0
    assert snapshot.yes_ask_size == 15.0
    assert snapshot.timestamp.isoformat().startswith("2026-05-30T")
    assert snapshot.metadata["book_hash"] == "book_hash"
    assert len(snapshot.metadata["bids"]) == 2


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


def test_capture_cli_discovers_polymarket_active_book(tmp_path: Path, capsys, monkeypatch) -> None:
    module = _load_capture_cli()
    raw_path = tmp_path / "polymarket.jsonl"
    manifest_path = tmp_path / "polymarket_manifest.json"

    class _Response:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self._payload

    def fake_get(url, *, params=None, timeout=0):
        assert timeout == 10.0
        if url == "https://gamma.example/markets":
            return _Response(
                [
                    {
                        "id": "540817",
                        "question": "Example market?",
                        "slug": "example-market",
                        "enableOrderBook": True,
                        "clobTokenIds": '["token_yes","token_no"]',
                    }
                ]
            )
        assert url == "https://clob.example/book"
        assert params == {"token_id": "token_yes"}
        return _Response(
            {
                "market": "0xabc",
                "asset_id": "token_yes",
                "timestamp": "1780172484142",
                "bids": [{"price": "0.41", "size": "12"}],
                "asks": [{"price": "0.43", "size": "8"}],
            }
        )

    monkeypatch.setattr(module.requests, "get", fake_get)

    rc = module.main(
        [
            "--polymarket-active-book",
            "--out",
            str(raw_path),
            "--manifest-out",
            str(manifest_path),
            "--source",
            "polymarket_clob",
            "--gamma-markets-url",
            "https://gamma.example/markets",
            "--clob-book-url",
            "https://clob.example/book",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    snapshots = load_prediction_market_snapshot_jsonl(raw_path)
    assert rc == 0
    assert payload["ok"] is True
    assert payload["row_count"] == 1
    assert snapshots[0].market_id == "0xabc"
    assert snapshots[0].yes_bid == 0.41
    assert snapshots[0].metadata["question"] == "Example market?"


def test_capture_cli_discovers_multiple_polymarket_books(tmp_path: Path, capsys, monkeypatch) -> None:
    module = _load_capture_cli()
    raw_path = tmp_path / "polymarket_multi.jsonl"
    manifest_path = tmp_path / "polymarket_multi_manifest.json"
    requested_tokens: list[str] = []

    class _Response:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self._payload

    def fake_get(url, *, params=None, timeout=0):
        if url == "https://gamma.example/markets":
            return _Response(
                [
                    {
                        "id": "m1",
                        "conditionId": "condition-1",
                        "question": "First market?",
                        "slug": "first-market",
                        "enableOrderBook": True,
                        "acceptingOrders": True,
                        "liquidity": "1000",
                        "volume": "500",
                        "clobTokenIds": '["m1_yes","m1_no"]',
                    },
                    {
                        "id": "m2",
                        "conditionId": "condition-2",
                        "question": "Second market?",
                        "slug": "second-market",
                        "enableOrderBook": True,
                        "acceptingOrders": True,
                        "liquidity": "2000",
                        "volume": "600",
                        "clobTokenIds": '["m2_yes","m2_no"]',
                    },
                ]
            )
        assert url == "https://clob.example/book"
        token = params["token_id"]
        requested_tokens.append(token)
        return _Response(
            {
                "market": f"condition-{token[:2]}",
                "asset_id": token,
                "timestamp": "1780172484142",
                "bids": [{"price": "0.40", "size": "10"}],
                "asks": [{"price": "0.42", "size": "9"}],
            }
        )

    monkeypatch.setattr(module.requests, "get", fake_get)

    rc = module.main(
        [
            "--polymarket-active-book",
            "--out",
            str(raw_path),
            "--manifest-out",
            str(manifest_path),
            "--source",
            "polymarket_clob",
            "--gamma-markets-url",
            "https://gamma.example/markets",
            "--clob-book-url",
            "https://clob.example/book",
            "--markets-per-poll",
            "2",
            "--tokens-per-market",
            "2",
            "--max-snapshots",
            "3",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    snapshots = load_prediction_market_snapshot_jsonl(raw_path)
    assert rc == 0
    assert payload["ok"] is True
    assert payload["row_count"] == 3
    assert requested_tokens == ["m1_yes", "m1_no", "m2_yes"]
    assert [snapshot.outcome_id for snapshot in snapshots] == ["m1_yes", "m1_no", "m2_yes"]
    assert snapshots[0].metadata["gamma_market_id"] == "m1"
    assert snapshots[2].metadata["question"] == "Second market?"


def test_capture_cli_writes_polymarket_sidecars(tmp_path: Path, capsys, monkeypatch) -> None:
    module = _load_capture_cli()
    raw_path = tmp_path / "polymarket_sidecars.jsonl"
    manifest_path = tmp_path / "polymarket_sidecars_manifest.json"
    market_metadata_path = tmp_path / "market_metadata.jsonl"
    trades_path = tmp_path / "trades.jsonl"
    fees_path = tmp_path / "fees.jsonl"

    class _Response:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self._payload

    def fake_get(url, *, params=None, timeout=0):
        if url == "https://gamma.example/markets":
            return _Response(
                [
                    {
                        "id": "m1",
                        "conditionId": "condition-1",
                        "question": "First market?",
                        "slug": "first-market",
                        "enableOrderBook": True,
                        "acceptingOrders": True,
                        "endDate": "2026-06-01T00:00:00Z",
                        "resolutionSource": "official-source",
                        "liquidity": "1000",
                        "volume": "500",
                        "bestBid": "0.40",
                        "bestAsk": "0.42",
                        "clobTokenIds": '["m1_yes","m1_no"]',
                    }
                ]
            )
        if url == "https://clob.example/book":
            return _Response(
                {
                    "market": "condition-1",
                    "asset_id": params["token_id"],
                    "timestamp": "1780172484142",
                    "bids": [{"price": "0.40", "size": "10"}],
                    "asks": [{"price": "0.42", "size": "9"}],
                    "min_order_size": "5",
                    "tick_size": "0.01",
                }
            )
        if url == "https://clob.example/clob-markets/condition-1":
            return _Response({"mos": 5, "mts": 0.01, "mbf": 1000})
        if url == "https://clob.example/fee-rate":
            return _Response({"base_fee": 1000})
        if url == "https://data.example/trades":
            assert params["market"] == "condition-1"
            assert params["limit"] == 7
            return _Response(
                [
                    {
                        "conditionId": "condition-1",
                        "asset": "m1_yes",
                        "side": "BUY",
                        "price": 0.41,
                        "size": 3.0,
                        "timestamp": 1780172500,
                    }
                ]
            )
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr(module.requests, "get", fake_get)

    rc = module.main(
        [
            "--polymarket-active-book",
            "--out",
            str(raw_path),
            "--manifest-out",
            str(manifest_path),
            "--source",
            "polymarket_clob",
            "--gamma-markets-url",
            "https://gamma.example/markets",
            "--clob-book-url",
            "https://clob.example/book",
            "--clob-market-info-url",
            "https://clob.example/clob-markets",
            "--fee-rate-url",
            "https://clob.example/fee-rate",
            "--data-trades-url",
            "https://data.example/trades",
            "--tokens-per-market",
            "2",
            "--max-snapshots",
            "2",
            "--trades-limit",
            "7",
            "--market-metadata-out",
            str(market_metadata_path),
            "--trades-out",
            str(trades_path),
            "--fees-out",
            str(fees_path),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    market_rows = [
        json.loads(line) for line in market_metadata_path.read_text(encoding="utf-8").splitlines()
    ]
    trade_rows = [json.loads(line) for line in trades_path.read_text(encoding="utf-8").splitlines()]
    fee_rows = [json.loads(line) for line in fees_path.read_text(encoding="utf-8").splitlines()]

    assert rc == 0
    assert payload["ok"] is True
    assert payload["metadata"]["sidecar_artifacts"]["market_metadata"]["row_count"] == 1
    assert payload["metadata"]["sidecar_artifacts"]["trades"]["row_count"] == 1
    assert payload["metadata"]["sidecar_artifacts"]["fees"]["row_count"] == 2
    assert manifest["metadata"]["sidecar_artifacts"] == payload["metadata"]["sidecar_artifacts"]
    assert market_rows[0]["resolution_source"] == "official-source"
    assert market_rows[0]["clob_market_info"]["mbf"] == 1000
    assert trade_rows[0]["asset"] == "m1_yes"
    assert fee_rows[0]["fee_rate"]["base_fee"] == 1000
