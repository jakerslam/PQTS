#!/usr/bin/env python3
"""Capture prediction-market raw snapshots into replayable JSONL artifacts."""

from __future__ import annotations

import argparse
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


def _discover_polymarket_book(args: argparse.Namespace) -> dict[str, Any]:
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

    token_index = max(int(args.token_index), 0)
    for market in payload:
        if not isinstance(market, dict):
            continue
        if market.get("enableOrderBook") is False:
            continue
        token_ids = _parse_token_ids(market.get("clobTokenIds"))
        if not token_ids or token_index >= len(token_ids):
            continue
        token_id = token_ids[token_index]
        book_response = requests.get(
            str(args.clob_book_url),
            params={"token_id": token_id},
            timeout=float(args.timeout_seconds),
        )
        book_response.raise_for_status()
        book = book_response.json()
        if not isinstance(book, dict):
            raise TypeError("Polymarket CLOB book response must be a JSON object")
        metadata = dict(book.get("metadata", {}) or {})
        metadata.update(
            {
                "gamma_market_id": market.get("id", ""),
                "question": market.get("question", ""),
                "slug": market.get("slug", ""),
                "clob_token_index": token_index,
                "gamma_markets_url": str(args.gamma_markets_url),
                "clob_book_url": str(args.clob_book_url),
            }
        )
        book["metadata"] = metadata
        return book
    raise RuntimeError("no active Polymarket CLOB market with token IDs was found")


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
    parser.add_argument("--token-index", type=int, default=0)
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
                payload = _discover_polymarket_book(args)
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
        else:  # pragma: no cover - argparse makes this unreachable.
            raise RuntimeError("no capture source selected")
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1

    payload = manifest.to_dict()
    payload["ok"] = True
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
