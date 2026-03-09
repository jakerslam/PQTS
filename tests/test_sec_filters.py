"""Tests for unit-aware and form-scoped SEC extraction filters."""

from __future__ import annotations

from adapters.sec.filters import (
    extract_companyconcept_series,
    extract_companyfacts_series,
    filter_by_forms,
    filter_by_unit,
)


def test_filter_by_unit_and_forms() -> None:
    class _Row:
        def __init__(self, unit: str, form: str):  # noqa: ANN204
            self.unit = unit
            self.form = form

    rows = [_Row("USD", "10-K"), _Row("shares", "10-Q"), _Row("USD", "8-K")]
    assert len(filter_by_unit(rows, "USD")) == 2
    assert len(filter_by_forms(rows, ("10-K", "10-Q"))) == 2


def test_extract_companyfacts_series_applies_unit_and_form_scopes() -> None:
    payload = {
        "cik": 320193,
        "facts": {
            "us-gaap": {
                "Assets": {
                    "units": {
                        "USD": [
                            {"val": 1.0, "form": "10-K"},
                            {"val": 2.0, "form": "10-Q"},
                        ],
                        "shares": [{"val": 3.0, "form": "10-K"}],
                    }
                }
            }
        },
    }
    rows = extract_companyfacts_series(
        payload,
        taxonomy="us-gaap",
        concept="Assets",
        unit="USD",
        forms=("10-Q",),
    )
    assert len(rows) == 1
    assert rows[0].value == 2.0


def test_extract_companyconcept_series_applies_filters() -> None:
    payload = {
        "units": {
            "USD": [{"val": 10.0, "form": "10-K"}, {"val": 12.0, "form": "10-Q"}],
            "shares": [{"val": 99.0, "form": "10-Q"}],
        }
    }
    rows = extract_companyconcept_series(
        payload,
        cik=789019,
        taxonomy="us-gaap",
        concept="Assets",
        unit="USD",
        forms=("10-K",),
    )
    assert len(rows) == 1
    assert rows[0].value == 10.0
