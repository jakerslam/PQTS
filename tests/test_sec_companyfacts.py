"""Tests for SEC companyfacts taxonomy traversal."""

from __future__ import annotations

from adapters.sec.companyfacts import ingest_companyfacts, traverse_companyfacts


def test_traverse_companyfacts_handles_dei_and_us_gaap() -> None:
    payload = {
        "cik": 320193,
        "facts": {
            "dei": {
                "EntityCommonStockSharesOutstanding": {
                    "units": {
                        "shares": [
                            {"val": 10.0, "end": "2024-09-30", "form": "10-Q", "accn": "0001"}
                        ]
                    }
                }
            },
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {"USD": [{"val": 12345.0, "end": "2024-09-30", "form": "10-Q"}]}
                }
            },
        },
    }
    rows = traverse_companyfacts(payload)
    assert len(rows) == 2
    concepts = {row.concept for row in rows}
    assert "EntityCommonStockSharesOutstanding" in concepts
    assert "RevenueFromContractWithCustomerExcludingAssessedTax" in concepts


def test_traverse_companyfacts_is_missing_tag_safe() -> None:
    payload = {"cik": 42, "facts": {"dei": {}}}
    rows = traverse_companyfacts(payload)
    assert rows == []


def test_ingest_companyfacts_builds_expected_endpoint() -> None:
    class _StubClient:
        def get_json(self, path: str):  # noqa: ANN202
            assert path == "/api/xbrl/companyfacts/CIK0000789019.json"
            return {
                "cik": 789019,
                "facts": {
                    "us-gaap": {
                        "Assets": {"units": {"USD": [{"val": 1.0, "end": "2024-12-31"}]}}
                    }
                },
            }

    rows = ingest_companyfacts(_StubClient(), 789019)  # type: ignore[arg-type]
    assert len(rows) == 1
    assert rows[0].concept == "Assets"
