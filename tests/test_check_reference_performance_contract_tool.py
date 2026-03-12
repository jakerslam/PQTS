from __future__ import annotations

import json
from pathlib import Path

from tools.check_reference_performance_contract import evaluate_reference_performance_contract


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_reference_performance_contract_passes_repo_default() -> None:
    errors = evaluate_reference_performance_contract(Path("results/reference_performance_latest.json"))
    assert errors == []


def test_reference_performance_contract_flags_missing_fields(tmp_path: Path) -> None:
    payload = {
        "generated_at": "2026-03-11T00:00:00+00:00",
        "bundle_count": 1,
        "bundles": [{}],
    }
    ref = tmp_path / "reference_performance_latest.json"
    _write_json(ref, payload)
    errors = evaluate_reference_performance_contract(ref)
    assert any("missing top-level key: schema_version" in item for item in errors)
    assert any("bundle[0] missing key: trust_label" in item for item in errors)
