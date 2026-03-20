from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import run_production_readiness_checks


def test_production_readiness_cli_writes_report(tmp_path, monkeypatch) -> None:
    payload = {
        "recovery_objectives": [{"environment": "canary", "rto_minutes": 20, "rpo_minutes": 5}],
        "recovery_measurements": [{"environment": "canary", "measured_rto_minutes": 15, "measured_rpo_minutes": 3}],
        "backup_manifests": [{"artifact_id": "ledger", "target_store": "s3", "checksum": "abc", "backup_ok": True}],
        "restore_drills": [{"artifact_id": "ledger", "restore_minutes": 10, "data_loss_minutes": 1, "passed": True}],
        "release_artifacts": [{"artifact_id": "wheel", "signed_provenance": True, "sbom_present": True, "sbom_validated": True}],
        "migration": {"preflight_ok": True, "dry_run_ok": True, "rollback_rehearsal_ok": True},
        "error_budget": {
            "api_availability_consumed": 0.1,
            "order_pipeline_failure_consumed": 0.1,
            "stream_degradation_consumed": 0.1,
            "incident_latency_consumed": 0.1,
        },
        "chaos_drills": [{"dependency": "redis", "detection_seconds": 10, "recovery_seconds": 20, "invariant_violations": 0}],
        "secrets": [{"key_id": "api", "rotated_recently": True, "expired": False, "revocation_drill_minutes": 5}],
    }
    input_path = tmp_path / "in.json"
    out_path = tmp_path / "report.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_production_readiness_checks.py",
            "--input",
            str(input_path),
            "--out",
            str(out_path),
        ],
    )

    assert run_production_readiness_checks.main() == 0
    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report["recovery"]["promotion_eligible"] is True
    assert report["release_integrity"]["release_allowed"] is True
