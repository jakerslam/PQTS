"""Multilingual event-intel normalization and confidence gating."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.compaction_primitives import utc_now_iso as _utc_now_iso


@dataclass(frozen=True)
class MultilingualEventRecord:
    """Canonical representation of translated public-source event intel."""

    event_id: str
    source_ref: str
    original_language: str
    original_text: str
    translated_text: str
    translation_method: str
    translation_timestamp: str
    translation_confidence: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "source_ref": self.source_ref,
            "original_language": self.original_language,
            "original_text": self.original_text,
            "translated_text": self.translated_text,
            "translation_method": self.translation_method,
            "translation_timestamp": self.translation_timestamp,
            "translation_confidence": float(self.translation_confidence),
        }

    def __post_init__(self) -> None:
        if not str(self.event_id).strip():
            raise ValueError("event_id is required")
        if not str(self.source_ref).strip():
            raise ValueError("source_ref is required")
        if not str(self.original_language).strip():
            raise ValueError("original_language is required")
        if not str(self.original_text).strip():
            raise ValueError("original_text is required")
        if not str(self.translated_text).strip():
            raise ValueError("translated_text is required")
        if not str(self.translation_method).strip():
            raise ValueError("translation_method is required")
        if not str(self.translation_timestamp).strip():
            raise ValueError("translation_timestamp is required")
        confidence = float(self.translation_confidence)
        if confidence < 0.0 or confidence > 1.0:
            raise ValueError("translation_confidence must be in [0, 1]")


def normalize_multilingual_event(
    *,
    event_id: str,
    source_ref: str,
    original_language: str,
    original_text: str,
    translated_text: str,
    translation_method: str,
    translation_confidence: float,
    translation_timestamp: str | None = None,
) -> MultilingualEventRecord:
    return MultilingualEventRecord(
        event_id=str(event_id).strip(),
        source_ref=str(source_ref).strip(),
        original_language=str(original_language).strip().lower(),
        original_text=str(original_text).strip(),
        translated_text=str(translated_text).strip(),
        translation_method=str(translation_method).strip(),
        translation_timestamp=str(translation_timestamp or _utc_now_iso()),
        translation_confidence=float(translation_confidence),
    )


def evaluate_translation_gate(
    record: MultilingualEventRecord,
    *,
    block_threshold: float = 0.45,
    down_rank_threshold: float = 0.75,
) -> tuple[str, tuple[str, ...]]:
    confidence = float(record.translation_confidence)
    if confidence < float(block_threshold):
        return "block", ("translation_confidence_too_low",)
    if confidence < float(down_rank_threshold):
        return "down_rank", ("translation_confidence_marginal",)
    return "allow", ()


def build_event_extraction_payload(record: MultilingualEventRecord) -> dict[str, Any]:
    """Expose translated + original references for semantic-drift auditability."""
    return {
        "event_id": record.event_id,
        "source_ref": record.source_ref,
        "original_language": record.original_language,
        "original_text": record.original_text,
        "translated_text": record.translated_text,
        "translation_method": record.translation_method,
        "translation_timestamp": record.translation_timestamp,
        "translation_confidence": float(record.translation_confidence),
    }
