"""Replay manifests for prediction-market microstructure feature artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from core.hotpath_runtime import event_id
from research.prediction_market_microstructure import (
    PredictionMarketBookSnapshot,
    build_prediction_market_microstructure_features,
)

SCHEMA_VERSION = "prediction_market_microstructure_replay_v1"
FEATURE_BUILDER = (
    "research.prediction_market_microstructure."
    "build_prediction_market_microstructure_features"
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iso_or_empty(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


@dataclass(frozen=True)
class PredictionMarketReplayManifest:
    """Reproducibility manifest for one raw-snapshot-to-feature replay."""

    manifest_id: str
    schema_version: str
    source: str
    raw_snapshot_path: str
    feature_snapshot_path: str
    raw_sha256: str
    feature_sha256: str
    row_count: int
    market_count: int
    outcome_count: int
    start_ts: str
    end_ts: str
    feature_columns: tuple[str, ...]
    quality_flag_counts: dict[str, int]
    feature_builder: str = FEATURE_BUILDER
    created_at: str = field(default_factory=_utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["feature_columns"] = list(self.feature_columns)
        out["quality_flag_counts"] = dict(self.quality_flag_counts)
        out["metadata"] = dict(self.metadata)
        return out

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PredictionMarketReplayManifest":
        return cls(
            manifest_id=str(payload.get("manifest_id", "")).strip(),
            schema_version=str(payload.get("schema_version", SCHEMA_VERSION)).strip(),
            source=str(payload.get("source", "")).strip(),
            raw_snapshot_path=str(payload.get("raw_snapshot_path", "")).strip(),
            feature_snapshot_path=str(payload.get("feature_snapshot_path", "")).strip(),
            raw_sha256=str(payload.get("raw_sha256", "")).strip(),
            feature_sha256=str(payload.get("feature_sha256", "")).strip(),
            row_count=int(payload.get("row_count", 0) or 0),
            market_count=int(payload.get("market_count", 0) or 0),
            outcome_count=int(payload.get("outcome_count", 0) or 0),
            start_ts=str(payload.get("start_ts", "")).strip(),
            end_ts=str(payload.get("end_ts", "")).strip(),
            feature_columns=tuple(str(item) for item in payload.get("feature_columns", ())),
            quality_flag_counts={
                str(key): int(value)
                for key, value in dict(payload.get("quality_flag_counts", {}) or {}).items()
            },
            feature_builder=str(payload.get("feature_builder", FEATURE_BUILDER)).strip(),
            created_at=str(payload.get("created_at", "")).strip() or _utc_now_iso(),
            metadata=dict(payload.get("metadata", {}) or {}),
        )


def write_prediction_market_snapshot_jsonl(
    snapshots: Iterable[PredictionMarketBookSnapshot | dict[str, Any]],
    path: str | Path,
) -> Path:
    """Write raw snapshots as newline-delimited JSON for deterministic replay."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for item in snapshots:
            snapshot = (
                item
                if isinstance(item, PredictionMarketBookSnapshot)
                else PredictionMarketBookSnapshot.from_dict(item)
            )
            handle.write(json.dumps(snapshot.to_dict(), sort_keys=True) + "\n")
    return output_path


def load_prediction_market_snapshot_jsonl(path: str | Path) -> list[PredictionMarketBookSnapshot]:
    """Load raw prediction-market snapshots from a JSONL replay artifact."""

    input_path = Path(path)
    snapshots: list[PredictionMarketBookSnapshot] = []
    with input_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = line.strip()
            if not payload:
                continue
            row = json.loads(payload)
            if not isinstance(row, dict):
                raise TypeError("prediction-market snapshot rows must be JSON objects")
            snapshots.append(PredictionMarketBookSnapshot.from_dict(row))
    return snapshots


def build_prediction_market_feature_artifact(
    *,
    raw_snapshot_path: str | Path,
    feature_snapshot_path: str | Path,
    manifest_path: str | Path,
    source: str,
    max_staleness_seconds: float = 60.0,
    wide_spread_threshold_bps: float = 750.0,
    metadata: dict[str, Any] | None = None,
) -> PredictionMarketReplayManifest:
    """Replay raw snapshots into features and write a reproducibility manifest."""

    raw_path = Path(raw_snapshot_path)
    feature_path = Path(feature_snapshot_path)
    manifest_output_path = Path(manifest_path)
    snapshots = load_prediction_market_snapshot_jsonl(raw_path)
    frame = build_prediction_market_microstructure_features(
        snapshots,
        max_staleness_seconds=max_staleness_seconds,
        wide_spread_threshold_bps=wide_spread_threshold_bps,
    )
    if "resolved_probability" in frame.columns:
        raise RuntimeError("feature artifact must not contain future resolution labels")

    feature_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_json(feature_path, orient="records", lines=True, date_format="iso")

    quality_counts: dict[str, int] = {}
    if not frame.empty and "quality_flags" in frame.columns:
        for flags in frame["quality_flags"]:
            for flag in list(flags or ()):
                quality_counts[str(flag)] = quality_counts.get(str(flag), 0) + 1

    raw_hash = _sha256_file(raw_path)
    feature_hash = _sha256_file(feature_path)
    manifest = PredictionMarketReplayManifest(
        manifest_id=event_id("pm_replay", (raw_hash, feature_hash), hex_len=20),
        schema_version=SCHEMA_VERSION,
        source=str(source).strip(),
        raw_snapshot_path=str(raw_path),
        feature_snapshot_path=str(feature_path),
        raw_sha256=raw_hash,
        feature_sha256=feature_hash,
        row_count=int(len(frame)),
        market_count=int(frame["market_id"].nunique()) if not frame.empty else 0,
        outcome_count=int(frame[["market_id", "outcome_id"]].drop_duplicates().shape[0])
        if not frame.empty
        else 0,
        start_ts=_iso_or_empty(frame["timestamp"].min()) if not frame.empty else "",
        end_ts=_iso_or_empty(frame["timestamp"].max()) if not frame.empty else "",
        feature_columns=tuple(str(column) for column in frame.columns),
        quality_flag_counts=dict(sorted(quality_counts.items())),
        metadata={
            "max_staleness_seconds": float(max_staleness_seconds),
            "wide_spread_threshold_bps": float(wide_spread_threshold_bps),
            **dict(metadata or {}),
        },
    )

    manifest_output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_output_path.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def load_prediction_market_replay_manifest(path: str | Path) -> PredictionMarketReplayManifest:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("prediction-market replay manifest must be a JSON object")
    return PredictionMarketReplayManifest.from_dict(payload)
