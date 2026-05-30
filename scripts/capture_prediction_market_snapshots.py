#!/usr/bin/env python3
"""Capture prediction-market raw snapshots into replayable JSONL artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path[:] = [str(SRC), *sys.path]
if str(ROOT) not in sys.path:
    sys.path[:] = [str(ROOT), *sys.path]

from research.prediction_market_capture import append_prediction_market_capture  # noqa: E402


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def _append_jsonl_rows(rows: list[dict[str, Any]], path: str | Path, *, append: bool) -> None:
    if not rows:
        return
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append and output_path.exists() else "w"
    with output_path.open(mode, encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _artifact_descriptor(path: str | Path) -> dict[str, Any]:
    artifact_path = Path(path)
    if not artifact_path.exists():
        return {"path": str(artifact_path), "row_count": 0, "sha256": ""}
    return {
        "path": str(artifact_path),
        "row_count": _line_count(artifact_path),
        "sha256": _sha256_file(artifact_path),
    }


def _parse_metadata(rows: list[str]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for row in rows:
        key, sep, raw_value = str(row).partition("=")
        if not sep or not key.strip():
            raise ValueError(f"metadata must be KEY=VALUE, got: {row}")
        value: Any = raw_value
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        metadata[key.strip()] = value
    return metadata


def _read_jsonl_payloads(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise TypeError("input JSONL rows must be objects")
            rows.append(payload)
    return rows


def _fetch_url_payload(url: str, *, timeout_seconds: float) -> Any:
    response = requests.get(url, timeout=float(timeout_seconds))
    response.raise_for_status()
    return response.json()


def _fetch_json_or_error(url: str, *, params: dict[str, Any] | None, timeout_seconds: float) -> Any:
    try:
        response = requests.get(url, params=params, timeout=float(timeout_seconds))
        response.raise_for_status()
        return response.json()
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": str(exc),
            "url": url,
            "params": dict(params or {}),
        }


def _parse_token_ids(value: Any) -> list[str]:
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return [raw]
        return _parse_token_ids(parsed)
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _condition_id_from_book(book: dict[str, Any]) -> str:
    metadata = dict(book.get("metadata", {}) or {})
    return str(
        metadata.get("condition_id")
        or metadata.get("conditionId")
        or book.get("market")
        or book.get("conditionId")
        or ""
    ).strip()


def _token_id_from_book(book: dict[str, Any]) -> str:
    metadata = dict(book.get("metadata", {}) or {})
    return str(
        metadata.get("clob_token_id")
        or book.get("asset_id")
        or book.get("token_id")
        or ""
    ).strip()


def _polymarket_market_metadata_rows(
    books: list[dict[str, Any]],
    *,
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    captured_at = _now_iso()
    for book in books:
        condition_id = _condition_id_from_book(book)
        if not condition_id or condition_id in seen:
            continue
        seen.add(condition_id)
        metadata = dict(book.get("metadata", {}) or {})
        clob_market_info = _fetch_json_or_error(
            f"{str(args.clob_market_info_url).rstrip('/')}/{condition_id}",
            params=None,
            timeout_seconds=float(args.timeout_seconds),
        )
        rows.append(
            {
                "captured_at": captured_at,
                "source": "polymarket",
                "condition_id": condition_id,
                "gamma_market_id": metadata.get("gamma_market_id", ""),
                "question": metadata.get("question", ""),
                "slug": metadata.get("slug", ""),
                "end_date": metadata.get("end_date", ""),
                "resolution_source": metadata.get("resolution_source", ""),
                "accepting_orders": metadata.get("accepting_orders", ""),
                "gamma_liquidity": metadata.get("gamma_liquidity", ""),
                "gamma_volume": metadata.get("gamma_volume", ""),
                "gamma_best_bid": metadata.get("gamma_best_bid", ""),
                "gamma_best_ask": metadata.get("gamma_best_ask", ""),
                "clob_market_info": clob_market_info,
            }
        )
    return rows


def _polymarket_fee_rows(
    books: list[dict[str, Any]],
    *,
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    captured_at = _now_iso()
    for book in books:
        token_id = _token_id_from_book(book)
        if not token_id or token_id in seen:
            continue
        seen.add(token_id)
        rows.append(
            {
                "captured_at": captured_at,
                "source": "polymarket_clob",
                "condition_id": _condition_id_from_book(book),
                "token_id": token_id,
                "fee_rate": _fetch_json_or_error(
                    str(args.fee_rate_url),
                    params={"token_id": token_id},
                    timeout_seconds=float(args.timeout_seconds),
                ),
                "min_order_size": book.get("min_order_size", ""),
                "tick_size": book.get("tick_size", ""),
            }
        )
    return rows


def _polymarket_trade_rows(
    books: list[dict[str, Any]],
    *,
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    condition_ids = sorted(
        {condition_id for book in books if (condition_id := _condition_id_from_book(book))}
    )
    if not condition_ids:
        return []
    payload = _fetch_json_or_error(
        str(args.data_trades_url),
        params={
            "market": ",".join(condition_ids),
            "limit": max(int(args.trades_limit), 1),
        },
        timeout_seconds=float(args.timeout_seconds),
    )
    captured_at = _now_iso()
    if isinstance(payload, list):
        return [
            {
                "captured_at": captured_at,
                "source": "polymarket_data_api",
                "query_markets": condition_ids,
                **dict(row),
            }
            for row in payload
            if isinstance(row, dict)
        ]
    return [
        {
            "captured_at": captured_at,
            "source": "polymarket_data_api",
            "query_markets": condition_ids,
            "error_payload": payload,
        }
    ]


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _discover_polymarket_books(
    args: argparse.Namespace,
    *,
    max_books: int | None = None,
) -> list[dict[str, Any]]:
    response = requests.get(
        str(args.gamma_markets_url),
        params={
            "active": "true",
            "closed": "false",
            "limit": max(int(args.market_limit), 1),
        },
        timeout=float(args.timeout_seconds),
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise TypeError("Polymarket Gamma markets response must be a list")

    market_limit = max(int(args.markets_per_poll), 1)
    tokens_per_market = max(int(args.tokens_per_market), 1)
    max_book_count = None if max_books is None or int(max_books) <= 0 else int(max_books)
    start_token_index = max(int(args.token_index), 0)
    books: list[dict[str, Any]] = []
    for market in payload:
        if not isinstance(market, dict):
            continue
        if market.get("enableOrderBook") is False:
            continue
        token_ids = _parse_token_ids(market.get("clobTokenIds"))
        if not token_ids or start_token_index >= len(token_ids):
            continue
        token_slice = token_ids[start_token_index : start_token_index + tokens_per_market]
        for offset, token_id in enumerate(token_slice):
            book_response = requests.get(
                str(args.clob_book_url),
                params={"token_id": token_id},
                timeout=float(args.timeout_seconds),
            )
            book_response.raise_for_status()
            book = book_response.json()
            if not isinstance(book, dict):
                raise TypeError("Polymarket CLOB book response must be a JSON object")
            token_index = start_token_index + offset
            metadata = dict(book.get("metadata", {}) or {})
            metadata.update(
                {
                    "gamma_market_id": market.get("id", ""),
                    "condition_id": market.get("conditionId", ""),
                    "question": market.get("question", ""),
                    "slug": market.get("slug", ""),
                    "end_date": market.get("endDate", ""),
                    "resolution_source": market.get("resolutionSource", ""),
                    "accepting_orders": market.get("acceptingOrders", ""),
                    "gamma_liquidity": market.get("liquidity", ""),
                    "gamma_volume": market.get("volume", ""),
                    "gamma_best_bid": market.get("bestBid", ""),
                    "gamma_best_ask": market.get("bestAsk", ""),
                    "clob_token_id": token_id,
                    "clob_token_index": token_index,
                    "gamma_markets_url": str(args.gamma_markets_url),
                    "clob_book_url": str(args.clob_book_url),
                }
            )
            book["metadata"] = metadata
            books.append(book)
            if max_book_count is not None and len(books) >= max_book_count:
                break
        if max_book_count is not None and len(books) >= max_book_count:
            break
        if len(books) >= market_limit * tokens_per_market:
            break
    if not books:
        raise RuntimeError("no active Polymarket CLOB market with token IDs was found")
    return books


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input-jsonl", help="Backfill/capture from an existing JSONL feed.")
    source.add_argument("--snapshot-url", help="HTTP JSON endpoint returning one snapshot or a list.")
    source.add_argument(
        "--polymarket-active-book",
        action="store_true",
        help="Discover an active Polymarket market via Gamma and capture its CLOB book.",
    )
    parser.add_argument("--out", required=True, help="Output raw snapshot JSONL path.")
    parser.add_argument("--manifest-out", required=True, help="Output capture manifest JSON path.")
    parser.add_argument("--source", required=True, help="Data source label, e.g. polymarket_ws.")
    parser.add_argument("--append", action="store_true", help="Append to an existing raw file.")
    parser.add_argument("--max-snapshots", type=int, default=1)
    parser.add_argument("--poll-seconds", type=float, default=0.0)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument(
        "--gamma-markets-url",
        default="https://gamma-api.polymarket.com/markets",
        help="Polymarket Gamma markets URL used with --polymarket-active-book.",
    )
    parser.add_argument(
        "--clob-book-url",
        default="https://clob.polymarket.com/book",
        help="Polymarket CLOB book URL used with --polymarket-active-book.",
    )
    parser.add_argument("--market-limit", type=int, default=25)
    parser.add_argument(
        "--markets-per-poll",
        type=int,
        default=1,
        help="Maximum active Polymarket markets to capture each poll.",
    )
    parser.add_argument(
        "--tokens-per-market",
        type=int,
        default=1,
        help="Maximum CLOB token books to capture per market each poll.",
    )
    parser.add_argument("--token-index", type=int, default=0)
    parser.add_argument("--market-metadata-out", help="Optional JSONL path for market/resolution metadata.")
    parser.add_argument("--trades-out", help="Optional JSONL path for public Data API trade rows.")
    parser.add_argument("--fees-out", help="Optional JSONL path for CLOB fee-rate rows.")
    parser.add_argument(
        "--data-trades-url",
        default="https://data-api.polymarket.com/trades",
        help="Public Polymarket Data API trades endpoint.",
    )
    parser.add_argument(
        "--fee-rate-url",
        default="https://clob.polymarket.com/fee-rate",
        help="Polymarket CLOB fee-rate endpoint.",
    )
    parser.add_argument(
        "--clob-market-info-url",
        default="https://clob.polymarket.com/clob-markets",
        help="Polymarket CLOB market-info base URL.",
    )
    parser.add_argument("--trades-limit", type=int, default=100)
    parser.add_argument(
        "--metadata",
        action="append",
        default=[],
        help="Manifest metadata as KEY=VALUE. VALUE may be JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    sidecar_paths = [
        value
        for value in (args.market_metadata_out, args.trades_out, args.fees_out)
        if str(value or "").strip()
    ]
    sidecar_artifacts: dict[str, Any] = {}
    try:
        metadata = _parse_metadata(list(args.metadata or []))
        limit = max(int(args.max_snapshots), 0) or None
        if args.input_jsonl:
            payloads = _read_jsonl_payloads(args.input_jsonl)
            manifest = append_prediction_market_capture(
                payloads,
                raw_snapshot_path=args.out,
                source=args.source,
                manifest_path=args.manifest_out,
                append=bool(args.append),
                limit=limit,
                metadata=metadata,
            )
        elif args.snapshot_url:
            captured = 0
            manifest = None
            while limit is None or captured < limit:
                batch_limit = None if limit is None else max(limit - captured, 0)
                payload = _fetch_url_payload(
                    str(args.snapshot_url),
                    timeout_seconds=float(args.timeout_seconds),
                )
                manifest = append_prediction_market_capture(
                    [payload],
                    raw_snapshot_path=args.out,
                    source=args.source,
                    manifest_path=args.manifest_out,
                    append=bool(args.append or captured > 0),
                    limit=batch_limit,
                    metadata=metadata,
                )
                captured += int(manifest.metadata.get("batch_row_count", 0))
                if limit is not None and captured >= limit:
                    break
                if float(args.poll_seconds) > 0.0:
                    time.sleep(float(args.poll_seconds))
            if manifest is None:
                raise RuntimeError("no snapshots captured")
        elif args.polymarket_active_book:
            captured = 0
            manifest = None
            while limit is None or captured < limit:
                batch_limit = None if limit is None else max(limit - captured, 0)
                payloads = _discover_polymarket_books(args, max_books=batch_limit)
                if args.market_metadata_out:
                    _append_jsonl_rows(
                        _polymarket_market_metadata_rows(payloads, args=args),
                        args.market_metadata_out,
                        append=bool(args.append or captured > 0),
                    )
                if args.fees_out:
                    _append_jsonl_rows(
                        _polymarket_fee_rows(payloads, args=args),
                        args.fees_out,
                        append=bool(args.append or captured > 0),
                    )
                if args.trades_out:
                    _append_jsonl_rows(
                        _polymarket_trade_rows(payloads, args=args),
                        args.trades_out,
                        append=bool(args.append or captured > 0),
                    )
                manifest = append_prediction_market_capture(
                    payloads,
                    raw_snapshot_path=args.out,
                    source=args.source,
                    manifest_path=args.manifest_out,
                    append=bool(args.append or captured > 0),
                    limit=batch_limit,
                    metadata=metadata,
                )
                captured += int(manifest.metadata.get("batch_row_count", 0))
                if limit is not None and captured >= limit:
                    break
                if float(args.poll_seconds) > 0.0:
                    time.sleep(float(args.poll_seconds))
            if manifest is None:
                raise RuntimeError("no snapshots captured")
        else:  # pragma: no cover - argparse makes this unreachable.
            raise RuntimeError("no capture source selected")
        sidecar_artifacts = {
            "market_metadata": _artifact_descriptor(args.market_metadata_out)
            if args.market_metadata_out
            else {},
            "trades": _artifact_descriptor(args.trades_out) if args.trades_out else {},
            "fees": _artifact_descriptor(args.fees_out) if args.fees_out else {},
        }
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1

    payload = manifest.to_dict()
    if sidecar_paths:
        payload["metadata"] = {
            **dict(payload.get("metadata", {}) or {}),
            "sidecar_artifacts": sidecar_artifacts,
        }
        Path(args.manifest_out).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    payload["ok"] = True
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
