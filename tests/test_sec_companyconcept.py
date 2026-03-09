"""Tests for SEC companyconcept metric adapter."""

from __future__ import annotations

import pytest

from adapters.sec.companyconcept import (
    ingest_companyconcept,
    parse_companyconcept,
    validate_concept,
    validate_taxonomy,
)


def test_taxonomy_and_concept_validation() -> None:
    assert validate_taxonomy("us-gaap") == "us-gaap"
    assert validate_concept("Assets") == "Assets"
    with pytest.raises(ValueError):
        validate_taxonomy("x")
    with pytest.raises(ValueError):
        validate_concept("bad concept")


def test_parse_companyconcept_reads_unit_points() -> None:
    payload = {
        "units": {
            "USD": [
                {"val": 123.0, "end": "2024-12-31", "form": "10-K", "accn": "0001"},
                {"val": 100.0, "end": "2023-12-31", "form": "10-K", "accn": "0002"},
            ]
        }
    }
    rows = parse_companyconcept(payload, cik=789019, taxonomy="us-gaap", concept="Assets")
    assert len(rows) == 2
    assert rows[0].cik_str == "0000789019"
    assert rows[0].unit == "USD"


def test_ingest_companyconcept_uses_expected_endpoint() -> None:
    class _StubClient:
        def get_json(self, path: str):  # noqa: ANN202
            assert path == "/api/xbrl/companyconcept/CIK0000789019/us-gaap/Assets.json"
            return {"units": {"USD": [{"val": 1.0}]}}

    rows = ingest_companyconcept(_StubClient(), cik=789019, taxonomy="us-gaap", concept="Assets")  # type: ignore[arg-type]
    assert len(rows) == 1


def test_ingest_companyconcept_wraps_provider_errors() -> None:
    class _FailClient:
        def get_json(self, path: str):  # noqa: ANN202, ARG002
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        ingest_companyconcept(_FailClient(), cik=789019, taxonomy="us-gaap", concept="Assets")  # type: ignore[arg-type]
