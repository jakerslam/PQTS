"""SEC companyfacts taxonomy traversal (`dei`, `us-gaap`, etc.)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from adapters.sec.client import SECClient
from adapters.sec.utils import normalize_cik


@dataclass(frozen=True)
class CompanyFactPoint:
    cik_str: str
    taxonomy: str
    concept: str
    unit: str
    value: float
    end: str | None
    form: str | None
    accession_number: str | None
    filed: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def traverse_companyfacts(
    payload: dict[str, Any],
    *,
    taxonomies: tuple[str, ...] = ("dei", "us-gaap"),
) -> list[CompanyFactPoint]:
    cik_source = payload.get("cik", "0")
    try:
        cik_str = normalize_cik(cik_source)
    except ValueError:
        cik_str = "0000000000"
    facts = payload.get("facts", {})
    if not isinstance(facts, dict):
        return []

    points: list[CompanyFactPoint] = []
    for taxonomy in taxonomies:
        concepts = facts.get(taxonomy, {})
        if not isinstance(concepts, dict):
            continue
        for concept_name, concept_payload in concepts.items():
            if not isinstance(concept_payload, dict):
                continue
            units = concept_payload.get("units", {})
            if not isinstance(units, dict):
                continue
            for unit_name, unit_points in units.items():
                if not isinstance(unit_points, list):
                    continue
                for row in unit_points:
                    if not isinstance(row, dict):
                        continue
                    value_raw = row.get("val")
                    if value_raw is None:
                        continue
                    points.append(
                        CompanyFactPoint(
                            cik_str=cik_str,
                            taxonomy=taxonomy,
                            concept=concept_name,
                            unit=str(unit_name),
                            value=float(value_raw),
                            end=(str(row["end"]) if "end" in row and row["end"] else None),
                            form=(str(row["form"]) if "form" in row and row["form"] else None),
                            accession_number=(
                                str(row["accn"]) if "accn" in row and row["accn"] else None
                            ),
                            filed=(str(row["filed"]) if "filed" in row and row["filed"] else None),
                        )
                    )
    return points


def ingest_companyfacts(client: SECClient, cik: int | str) -> list[CompanyFactPoint]:
    cik_str = normalize_cik(cik)
    payload = client.get_json(f"/api/xbrl/companyfacts/CIK{cik_str}.json")
    return traverse_companyfacts(payload)
