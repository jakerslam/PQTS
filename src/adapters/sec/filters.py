"""Unit-aware and form-scoped filtering helpers for SEC datasets."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, TypeVar

from adapters.sec.companyconcept import CompanyConceptPoint, parse_companyconcept
from adapters.sec.companyfacts import CompanyFactPoint, traverse_companyfacts

T = TypeVar("T")


def _form_set(forms: Iterable[str] | None) -> set[str]:
    if forms is None:
        return set()
    return {str(item).strip().upper() for item in forms if str(item).strip()}


def filter_by_unit(rows: Iterable[T], unit: str | None) -> list[T]:
    values = list(rows)
    if not unit:
        return values
    target = str(unit).strip().lower()
    return [row for row in values if str(getattr(row, "unit", "")).strip().lower() == target]


def filter_by_forms(rows: Iterable[T], forms: Iterable[str] | None) -> list[T]:
    values = list(rows)
    allowed = _form_set(forms)
    if not allowed:
        return values
    return [
        row
        for row in values
        if str(getattr(row, "form", "") or "").strip().upper() in allowed
    ]


def extract_companyfacts_series(
    payload: dict[str, Any],
    *,
    taxonomy: str,
    concept: str,
    unit: str | None = None,
    forms: Iterable[str] | None = ("10-Q", "10-K"),
) -> list[CompanyFactPoint]:
    rows = [
        row
        for row in traverse_companyfacts(payload, taxonomies=(taxonomy,))
        if row.concept == concept
    ]
    rows = filter_by_unit(rows, unit)
    rows = filter_by_forms(rows, forms)
    return rows


def extract_companyconcept_series(
    payload: dict[str, Any],
    *,
    cik: int | str,
    taxonomy: str,
    concept: str,
    unit: str | None = None,
    forms: Iterable[str] | None = ("10-Q", "10-K"),
) -> list[CompanyConceptPoint]:
    rows = parse_companyconcept(payload, cik=cik, taxonomy=taxonomy, concept=concept)
    rows = filter_by_unit(rows, unit)
    rows = filter_by_forms(rows, forms)
    return rows
