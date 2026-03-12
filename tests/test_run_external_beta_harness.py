from __future__ import annotations

import json
from pathlib import Path

from scripts.run_external_beta_harness import main


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_external_beta_harness_writes_summary_and_updates_registry(tmp_path: Path, monkeypatch) -> None:
    registry = tmp_path / "cohort_registry.json"
    _write(
        registry,
        {
            "schema_version": "1",
            "updated_at": "2026-03-10T00:00:00Z",
            "cohorts": [
                {
                    "release_window": "2026-03",
                    "status": "planned",
                    "external_beginner_participants": 0,
                    "external_pro_participants": 0,
                    "internal_proxy_participants": 2,
                    "channels": ["discord"],
                    "owner": "research-ops",
                }
            ],
        },
    )
    user_research = tmp_path / "user_research.md"
    user_research.write_text("- `release_window: 2026-03`\n", encoding="utf-8")
    beginner = tmp_path / "reports" / "2026-03_beginner.json"
    professional = tmp_path / "reports" / "2026-03_professional.json"
    _write(
        beginner,
        {
            "persona": "beginner",
            "participant_count": 2,
            "task_completion_rate": 0.75,
            "median_time_to_first_meaningful_result_minutes": 4.5,
            "top_blockers": ["credentials confusion"],
            "channels": ["discord"],
        },
    )
    _write(
        professional,
        {
            "persona": "professional",
            "participant_count": 1,
            "task_completion_rate": 1.0,
            "median_time_to_first_meaningful_result_minutes": 2.0,
            "top_blockers": ["want richer order diagnostics"],
            "channels": ["github_issues"],
        },
    )
    summary = tmp_path / "reports" / "summary.json"

    monkeypatch.setattr(
        "sys.argv",
        [
            "run_external_beta_harness.py",
            "--registry",
            str(registry),
            "--user-research",
            str(user_research),
            "--beginner-report",
            str(beginner),
            "--professional-report",
            str(professional),
            "--summary-out",
            str(summary),
            "--update-registry",
        ],
    )
    assert main() == 0

    written_summary = json.loads(summary.read_text(encoding="utf-8"))
    assert written_summary["release_window"] == "2026-03"
    assert written_summary["metrics"]["external_beginner_participants"] == 2
    assert written_summary["metrics"]["external_pro_participants"] == 1

    written_registry = json.loads(registry.read_text(encoding="utf-8"))
    row = written_registry["cohorts"][0]
    assert row["status"] == "completed"
    assert row["external_beginner_participants"] == 2
    assert row["external_pro_participants"] == 1


def test_external_beta_harness_fails_on_invalid_schema(tmp_path: Path, monkeypatch) -> None:
    registry = tmp_path / "cohort_registry.json"
    _write(registry, {"schema_version": "1", "cohorts": []})
    user_research = tmp_path / "user_research.md"
    user_research.write_text("- `release_window: 2026-03`\n", encoding="utf-8")
    beginner = tmp_path / "reports" / "2026-03_beginner.json"
    professional = tmp_path / "reports" / "2026-03_professional.json"
    _write(beginner, {"persona": "beginner"})
    _write(professional, {"persona": "professional"})

    monkeypatch.setattr(
        "sys.argv",
        [
            "run_external_beta_harness.py",
            "--registry",
            str(registry),
            "--user-research",
            str(user_research),
            "--beginner-report",
            str(beginner),
            "--professional-report",
            str(professional),
        ],
    )
    assert main() == 2
