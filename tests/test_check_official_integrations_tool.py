from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from tools.check_official_integrations import evaluate_integrations, load_integration_index


def test_load_integration_index_reads_array(tmp_path: Path) -> None:
    target = tmp_path / "integrations.json"
    target.write_text(
        json.dumps(
            [
                {
                    "id": "x",
                    "provider": "Polymarket",
                    "repo_url": "https://github.com/Polymarket/py-clob-client",
                    "surface": "sdk",
                    "owner": "team",
                    "status": "active",
                    "last_reviewed": "2026-03-10",
                }
            ]
        ),
        encoding="utf-8",
    )
    rows = load_integration_index(target)
    assert len(rows) == 1
    assert rows[0]["id"] == "x"


def test_evaluate_integrations_accepts_valid_rows() -> None:
    rows = [
        {
            "id": "pmkt-cli",
            "provider": "Polymarket",
            "repo_url": "https://github.com/Polymarket/polymarket-cli",
            "surface": "cli",
            "owner": "integration-team",
            "status": "active",
            "last_reviewed": "2026-03-10",
        }
    ]
    errors = evaluate_integrations(rows, today=date(2026, 3, 10), max_age_days=45)
    assert errors == []


def test_evaluate_integrations_flags_stale_and_duplicate_url() -> None:
    rows = [
        {
            "id": "a",
            "provider": "Polymarket",
            "repo_url": "https://github.com/Polymarket/polymarket-cli",
            "surface": "cli",
            "owner": "integration-team",
            "status": "active",
            "last_reviewed": "2025-12-01",
        },
        {
            "id": "b",
            "provider": "Polymarket",
            "repo_url": "https://github.com/Polymarket/polymarket-cli",
            "surface": "cli",
            "owner": "integration-team",
            "status": "active",
            "last_reviewed": "2026-03-10",
        },
    ]
    errors = evaluate_integrations(rows, today=date(2026, 3, 10), max_age_days=45)
    assert any("stale last_reviewed" in item for item in errors)
    assert any("duplicate repo_url" in item for item in errors)
