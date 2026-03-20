"""Run production-readiness contract checks and emit machine-readable verdicts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from analytics.production_readiness import (  # noqa: E402
    BackupManifest,
    ChaosDrillResult,
    ErrorBudgetWindow,
    MigrationEvidence,
    RecoveryMeasurement,
    RecoveryObjective,
    ReleaseArtifact,
    RestoreDrillArtifact,
    SecretState,
    evaluate_backup_restore,
    evaluate_chaos_window,
    evaluate_error_budget,
    evaluate_migration_readiness,
    evaluate_recovery_posture,
    evaluate_release_integrity,
    evaluate_secret_emergency,
)


def _read_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="JSON payload describing readiness artifacts")
    parser.add_argument("--out", default="data/reports/production_readiness/latest.json")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    payload = _read_json(args.input)

    recovery = evaluate_recovery_posture(
        objectives=[RecoveryObjective(**row) for row in payload.get("recovery_objectives", [])],
        measurements=[RecoveryMeasurement(**row) for row in payload.get("recovery_measurements", [])],
    )
    backup = evaluate_backup_restore(
        manifests=[BackupManifest(**row) for row in payload.get("backup_manifests", [])],
        drills=[RestoreDrillArtifact(**row) for row in payload.get("restore_drills", [])],
        max_restore_minutes=int(payload.get("max_restore_minutes", 30)),
        max_data_loss_minutes=int(payload.get("max_data_loss_minutes", 5)),
    )
    release = evaluate_release_integrity(
        [ReleaseArtifact(**row) for row in payload.get("release_artifacts", [])]
    )
    migration = evaluate_migration_readiness(MigrationEvidence(**payload.get("migration", {})))
    error_budget = evaluate_error_budget(
        ErrorBudgetWindow(**payload.get("error_budget", {})),
        max_consumed=float(payload.get("error_budget_max_consumed", 1.0)),
    )
    chaos = evaluate_chaos_window(
        drills=[ChaosDrillResult(**row) for row in payload.get("chaos_drills", [])],
        max_detection_seconds=int(payload.get("max_detection_seconds", 120)),
        max_recovery_seconds=int(payload.get("max_recovery_seconds", 600)),
    )
    secret = evaluate_secret_emergency(
        states=[SecretState(**row) for row in payload.get("secrets", [])],
        max_revocation_minutes=int(payload.get("max_revocation_minutes", 30)),
    )

    report = {
        "recovery": recovery.__dict__,
        "backup_restore": backup.__dict__,
        "release_integrity": release.__dict__,
        "migration": migration.__dict__,
        "error_budget": error_budget.__dict__,
        "chaos": chaos.__dict__,
        "secrets": secret.__dict__,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
