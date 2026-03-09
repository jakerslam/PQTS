"""Tests for strict function-call QA schema validator."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.function_call_schema import validate_function_call_batch, validate_function_call_item


def test_validate_function_call_item_accepts_valid_payload() -> None:
    item = validate_function_call_item(
        {
            "question": "What was revenue growth?",
            "answer": "Revenue grew 12% year-over-year.",
            "context": ["Q4 filing notes", "Management commentary"],
        }
    )
    assert item.question.startswith("What")
    assert len(item.context) == 2


def test_validate_function_call_item_rejects_extra_keys_in_strict_mode() -> None:
    with pytest.raises(ValueError, match="Unexpected keys"):
        validate_function_call_item(
            {
                "question": "q",
                "answer": "a",
                "context": "c",
                "extra": "nope",
            },
            strict=True,
        )


def test_validate_function_call_batch_enforces_max_items() -> None:
    with pytest.raises(ValueError, match="exceeds max_items"):
        validate_function_call_batch(
            [
                {"question": "q1", "answer": "a1", "context": "c1"},
                {"question": "q2", "answer": "a2", "context": "c2"},
            ],
            max_items=1,
        )


def test_validate_function_call_batch_reports_item_index() -> None:
    with pytest.raises(ValueError, match="index 2"):
        validate_function_call_batch(
            [
                {"question": "q1", "answer": "a1", "context": "c1"},
                {"question": "", "answer": "a2", "context": "c2"},
            ]
        )
