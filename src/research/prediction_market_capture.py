"""Append-only capture contracts for prediction-market raw snapshots."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from research.prediction_market_microstructure import PredictionMarketBookSnapshot
from research.prediction_market_replay import load_prediction_market_snapshot_jsonl

CAPTURE_SCHEMA_VERSION = "prediction_market_capture_v1"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _first_present(payload: dict[str, Any], names: tuple[str, ...], default: Any = None) -> Any:
    for name in names:
        if name in payload and payload[name] is not None:
            return payload[name]
    return default


def _payload_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, PredictionMarketBookSnapshot):
        return [payload.to_dict()]
    if isinstance(payload, list):
        rows: list[dict[str, Any]] = []
        for item in payload:
            rows.extend(_payload_rows(item))
        return rows
    if not isinstance(payload, dict):
        raise TypeError("prediction-market capture payloads must be JSON objects or lists")
    for key in ("snapshots", "markets", "data", "results"):
        nested = payload.get(key)
        if isinstance(nested, list):
            return _payload_rows(nested)
    return [payload]


def _best_book_level(levels: Any, *, side: str) -> tuple[float | None, float]:
    if not isinstance(levels, list):
        return None, 0.0
    best_price: float | None = None
    best_size = 0.0
    for level in levels:
        if not isinstance(level, dict):
            continue
        try:
            price = float(level.get("price"))
            size = max(float(level.get("size", 0.0)), 0.0)
        except (TypeError, ValueError):
            continue
        if best_price is None:
            best_price = price
            best_size = size
            continue
        if side == "bid" and price > best_price:
            best_price = price
            best_size = size
        if side == "ask" and price < best_price:
            best_price = price
            best_size = size
    return best_price, best_size


def _book_liquidity(payload: dict[str, Any]) -> float:
    total = 0.0
    for side in ("bids", "asks"):
        levels = payload.get(side)
        if not isinstance(levels, list):
            continue
        for level in levels:
            if not isinstance(level, dict):
                continue
            try:
                total += max(float(level.get("size", 0.0)), 0.0)
            except (TypeError, ValueError):
                continue
    return total


@dataclass(frozen=True)
class PredictionMarketCaptureManifest:
    """Manifest for an append-only raw prediction-market snapshot capture."""

    manifest_id: str
    schema_version: str
    source: str
    raw_snapshot_path: str
    raw_sha256: str
    row_count: int
    market_count: int
    outcome_count: int
    start_ts: str
    end_ts: str
    captured_at: str = field(default_factory=_utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["metadata"] = dict(self.metadata)
        return out

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PredictionMarketCaptureManifest":
        return cls(
            manifest_id=str(payload.get("manifest_id", "")).strip(),
            schema_version=str(payload.get("schema_version", CAPTURE_SCHEMA_VERSION)).strip(),
            source=str(payload.get("source", "")).strip(),
            raw_snapshot_path=str(payload.get("raw_snapshot_path", "")).strip(),
            raw_sha256=str(payload.get("raw_sha256", "")).strip(),
            row_count=int(payload.get("row_count", 0) or 0),
            market_count=int(payload.get("market_count", 0) or 0),
            outcome_count=int(payload.get("outcome_count", 0) or 0),
            start_ts=str(payload.get("start_ts", "")).strip(),
            end_ts=str(payload.get("end_ts", "")).strip(),
            captured_at=str(payload.get("captured_at", "")).strip() or _utc_now_iso(),
            metadata=dict(payload.get("metadata", {}) or {}),
        )


def normalize_prediction_market_capture_payload(
    payload: dict[str, Any] | PredictionMarketBookSnapshot,
    *,
    source: str,
) -> PredictionMarketBookSnapshot:
    """Normalize a venue/book payload into the canonical raw snapshot shape."""

    if isinstance(payload, PredictionMarketBookSnapshot):
        row = payload.to_dict()
    else:
        row = dict(payload)
    source_token = str(source or row.get("source") or "unknown").strip() or "unknown"
    book_bid, book_bid_size = _best_book_level(row.get("bids"), side="bid")
    book_ask, book_ask_size = _best_book_level(row.get("asks"), side="ask")
    yes_bid = _first_present(
        row,
        ("yes_bid", "best_bid", "bid"),
        book_bid if book_bid is not None else row.get("last_price"),
    )
    yes_ask = _first_present(
        row,
        ("yes_ask", "best_ask", "ask"),
        book_ask if book_ask is not None else row.get("last_price"),
    )
    normalized = {
        "market_id": _first_present(
            row,
            ("market_id", "condition_id", "conditionId", "question_id", "market", "id"),
            "",
        ),
        "outcome_id": _first_present(
            row,
            ("outcome_id", "token_id", "asset_id", "outcome", "clob_token_id"),
            "",
        ),
        "timestamp": _first_present(row, ("timestamp", "ts", "captured_at"), _utc_now()),
        "yes_bid": yes_bid,
        "yes_ask": yes_ask,
        "yes_bid_size": _first_present(
            row,
            ("yes_bid_size", "bid_size", "best_bid_size"),
            book_bid_size,
        ),
        "yes_ask_size": _first_present(
            row,
            ("yes_ask_size", "ask_size", "best_ask_size"),
            book_ask_size,
        ),
        "no_bid": _first_present(row, ("no_bid",), float("nan")),
        "no_ask": _first_present(row, ("no_ask",), float("nan")),
        "no_bid_size": _first_present(row, ("no_bid_size",), 0.0),
        "no_ask_size": _first_present(row, ("no_ask_size",), 0.0),
        "last_price": _first_present(row, ("last_price", "price", "mid"), float("nan")),
        "traded_volume": _first_present(row, ("traded_volume", "volume", "volume_num"), 0.0),
        "liquidity": _first_present(row, ("liquidity", "liquidity_num"), _book_liquidity(row)),
        "source": source_token,
        "sequence": _first_present(row, ("sequence", "seq"), 0),
        "resolved_probability": row.get("resolved_probability"),
        "metadata": {
            **dict(row.get("metadata", {}) or {}),
            "capture_source": source_token,
            "book_hash": row.get("hash", ""),
            "min_order_size": row.get("min_order_size", ""),
            "tick_size": row.get("tick_size", ""),
            "bids": row.get("bids", []),
            "asks": row.get("asks", []),
        },
    }
    return PredictionMarketBookSnapshot.from_dict(normalized)


def normalize_prediction_market_capture_payloads(
    payloads: Iterable[Any],
    *,
    source: str,
    limit: int | None = None,
) -> list[PredictionMarketBookSnapshot]:
    """Normalize one or more capture payloads into canonical snapshots."""

    snapshots: list[PredictionMarketBookSnapshot] = []
    max_rows = None if limit is None or int(limit) <= 0 else int(limit)
    for payload in payloads:
        for row in _payload_rows(payload):
            snapshots.append(normalize_prediction_market_capture_payload(row, source=source))
            if max_rows is not None and len(snapshots) >= max_rows:
                return snapshots
    return snapshots


def append_prediction_market_capture(
    payloads: Iterable[Any],
    *,
    raw_snapshot_path: str | Path,
    source: str,
    manifest_path: str | Path | None = None,
    append: bool = True,
    limit: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> PredictionMarketCaptureManifest:
    """Append normalized raw snapshots and write a capture manifest."""

    raw_path = Path(raw_snapshot_path)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    snapshots = normalize_prediction_market_capture_payloads(payloads, source=source, limit=limit)
    mode = "a" if append and raw_path.exists() else "w"
    with raw_path.open(mode, encoding="utf-8") as handle:
        for snapshot in snapshots:
            handle.write(json.dumps(snapshot.to_dict(), sort_keys=True) + "\n")

    all_snapshots = load_prediction_market_snapshot_jsonl(raw_path)
    raw_hash = _sha256_file(raw_path)
    timestamps = [snapshot.timestamp for snapshot in all_snapshots]
    manifest = PredictionMarketCaptureManifest(
        manifest_id=f"pm_capture_{raw_hash[:20]}",
        schema_version=CAPTURE_SCHEMA_VERSION,
        source=str(source).strip(),
        raw_snapshot_path=str(raw_path),
        raw_sha256=raw_hash,
        row_count=len(all_snapshots),
        market_count=len({snapshot.market_id for snapshot in all_snapshots}),
        outcome_count=len(
            {(snapshot.market_id, snapshot.outcome_id) for snapshot in all_snapshots}
        ),
        start_ts=min(timestamps).isoformat() if timestamps else "",
        end_ts=max(timestamps).isoformat() if timestamps else "",
        metadata={
            "batch_row_count": len(snapshots),
            "append": bool(mode == "a"),
            **dict(metadata or {}),
        },
    )
    if manifest_path is not None:
        output_path = Path(manifest_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return manifest


def load_prediction_market_capture_manifest(
    path: str | Path,
) -> PredictionMarketCaptureManifest:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("prediction-market capture manifest must be a JSON object")
    return PredictionMarketCaptureManifest.from_dict(payload)
