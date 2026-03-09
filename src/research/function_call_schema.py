"""Strict function-call schema validation for QA dataset outputs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class QAFunctionCallItem:
    question: str
    answer: str
    context: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


ALLOWED_KEYS = {"question", "answer", "context"}


def _as_non_empty_str(value: Any, *, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required and must be non-empty.")
    return text


def _normalize_context(value: Any) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("context must be non-empty.")
        return [text]
    if not isinstance(value, list):
        raise ValueError("context must be a string or list of strings.")
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            out.append(text)
    if not out:
        raise ValueError("context list must include at least one non-empty item.")
    return out


def validate_function_call_item(payload: dict[str, Any], *, strict: bool = True) -> QAFunctionCallItem:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict.")
    keys = set(payload.keys())
    missing = ALLOWED_KEYS - keys
    if missing:
        raise ValueError(f"Missing required keys: {sorted(missing)}")
    if strict:
        extra = keys - ALLOWED_KEYS
        if extra:
            raise ValueError(f"Unexpected keys present in strict mode: {sorted(extra)}")

    question = _as_non_empty_str(payload.get("question"), field_name="question")
    answer = _as_non_empty_str(payload.get("answer"), field_name="answer")
    context = _normalize_context(payload.get("context"))
    return QAFunctionCallItem(question=question, answer=answer, context=context)


def validate_function_call_batch(
    payloads: Iterable[dict[str, Any]],
    *,
    strict: bool = True,
    max_items: int | None = None,
) -> list[QAFunctionCallItem]:
    items = list(payloads)
    if max_items is not None and len(items) > int(max_items):
        raise ValueError(f"Batch size {len(items)} exceeds max_items={int(max_items)}.")
    validated: list[QAFunctionCallItem] = []
    for idx, payload in enumerate(items, start=1):
        try:
            validated.append(validate_function_call_item(payload, strict=strict))
        except ValueError as exc:
            raise ValueError(f"Invalid function-call item at index {idx}: {exc}") from exc
    return validated
