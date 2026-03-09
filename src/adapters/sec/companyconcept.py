"""SEC companyconcept adapter for targeted concept time-series retrieval."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from adapters.sec.client import SECClient
from adapters.sec.utils import normalize_cik

_TAXONOMY_RE = re.compile(r"^[a-zA-Z0-9_-]{2,32}$")
_CONCEPT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{1,120}$")


def validate_taxonomy(value: str) -> str:
    taxonomy = str(value or "").strip()
    if not _TAXONOMY_RE.fullmatch(taxonomy):
        raise ValueError(f"Invalid taxonomy `{value}`.")
    return taxonomy


def validate_concept(value: str) -> str:
    concept = str(value or "").strip()
    if not _CONCEPT_RE.fullmatch(concept):
        raise ValueError(f"Invalid concept `{value}`.")
    return concept


@dataclass(frozen=True)
class CompanyConceptPoint:
    cik_str: str
    taxonomy: str
    concept: str
    unit: str
    value: float
    end: str | None
    form: str | None
    filed: str | None
    accession_number: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_companyconcept(
    payload: dict[str, Any],
    *,
    cik: int | str,
    taxonomy: str,
    concept: str,
) -> list[CompanyConceptPoint]:
    cik_str = normalize_cik(cik)
    tax = validate_taxonomy(taxonomy)
    con = validate_concept(concept)
    units = payload.get("units", {})
    if not isinstance(units, dict):
        return []

    rows: list[CompanyConceptPoint] = []
    for unit_name, points in units.items():
        if not isinstance(points, list):
            continue
        for row in points:
            if not isinstance(row, dict) or row.get("val") is None:
                continue
            rows.append(
                CompanyConceptPoint(
                    cik_str=cik_str,
                    taxonomy=tax,
                    concept=con,
                    unit=str(unit_name),
                    value=float(row["val"]),
                    end=(str(row["end"]) if row.get("end") else None),
                    form=(str(row["form"]) if row.get("form") else None),
                    filed=(str(row["filed"]) if row.get("filed") else None),
                    accession_number=(str(row["accn"]) if row.get("accn") else None),
                )
            )
    return rows


def ingest_companyconcept(
    client: SECClient,
    *,
    cik: int | str,
    taxonomy: str,
    concept: str,
) -> list[CompanyConceptPoint]:
    cik_str = normalize_cik(cik)
    tax = validate_taxonomy(taxonomy)
    con = validate_concept(concept)
    path = f"/api/xbrl/companyconcept/CIK{cik_str}/{tax}/{con}.json"
    try:
        payload = client.get_json(path)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load SEC companyconcept for CIK {cik_str}, taxonomy {tax}, concept {con}."
        ) from exc
    return parse_companyconcept(payload, cik=cik_str, taxonomy=tax, concept=con)
