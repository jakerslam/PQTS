from __future__ import annotations

import json
from pathlib import Path

from scripts.compute_growth_kpi_targets import main


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_compute_growth_kpi_targets_generates_digest_and_doc(tmp_path: Path, monkeypatch) -> None:
    history = tmp_path / "history.json"
    _write_json(
        history,
        {
            "schema_version": "1",
            "months": [
                {
                    "month": "2026-03",
                    "stars": {"actual": 1, "target": 10},
                    "forks": {"actual": 0, "target": 3},
                    "docs_engagement": {"actual": 20, "target": 30},
                    "onboarding_conversion_pct": {"actual": 0.30, "target": 0.45},
                },
                {
                    "month": "2026-04",
                    "stars": {"actual": 2, "target": 12},
                    "forks": {"actual": 1, "target": 4},
                    "docs_engagement": {"actual": 25, "target": 35},
                    "onboarding_conversion_pct": {"actual": 0.32, "target": 0.46},
                },
            ],
        },
    )
    review_doc = tmp_path / "GROWTH_KPI_REVIEW.md"
    review_doc.write_text("# Growth KPI Review\n", encoding="utf-8")
    out_json = tmp_path / "GROWTH_KPI_DIGEST.json"

    monkeypatch.setattr(
        "sys.argv",
        [
            "compute_growth_kpi_targets.py",
            "--history",
            str(history),
            "--review-doc",
            str(review_doc),
            "--out-json",
            str(out_json),
        ],
    )
    assert main() == 0
    digest = json.loads(out_json.read_text(encoding="utf-8"))
    assert digest["roadmap_reprioritization_required"] is True
    assert digest["max_consecutive_miss_windows"] >= 2
    assert "GROWTH_KPI_DIGEST:START" in review_doc.read_text(encoding="utf-8")


def test_compute_growth_kpi_targets_check_mode_detects_stale_artifacts(tmp_path: Path, monkeypatch) -> None:
    history = tmp_path / "history.json"
    _write_json(
        history,
        {
            "schema_version": "1",
            "months": [
                {
                    "month": "2026-03",
                    "stars": {"actual": 3, "target": 2},
                    "forks": {"actual": 2, "target": 1},
                    "docs_engagement": {"actual": 50, "target": 30},
                    "onboarding_conversion_pct": {"actual": 0.6, "target": 0.45},
                }
            ],
        },
    )
    review_doc = tmp_path / "GROWTH_KPI_REVIEW.md"
    review_doc.write_text("# stale\n", encoding="utf-8")
    out_json = tmp_path / "GROWTH_KPI_DIGEST.json"
    out_json.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "compute_growth_kpi_targets.py",
            "--history",
            str(history),
            "--review-doc",
            str(review_doc),
            "--out-json",
            str(out_json),
            "--check",
        ],
    )
    assert main() == 2
