from __future__ import annotations

from analytics.production_readiness import (
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


def test_recovery_posture_blocks_when_rto_rpo_exceeded() -> None:
    decision = evaluate_recovery_posture(
        objectives=[RecoveryObjective(environment="canary", rto_minutes=15, rpo_minutes=5)],
        measurements=[RecoveryMeasurement(environment="canary", measured_rto_minutes=22, measured_rpo_minutes=3)],
    )
    assert decision.promotion_eligible is False
    assert "rto_exceeded:canary" in decision.reason_codes


def test_backup_restore_requires_valid_drill_evidence() -> None:
    decision = evaluate_backup_restore(
        manifests=[BackupManifest(artifact_id="ledger", target_store="s3", checksum="abc", backup_ok=True)],
        drills=[RestoreDrillArtifact(artifact_id="ledger", restore_minutes=45, data_loss_minutes=2, passed=True)],
        max_restore_minutes=30,
        max_data_loss_minutes=5,
    )
    assert decision.policy_ok is False
    assert "restore_too_slow:ledger" in decision.reason_codes


def test_release_migration_budget_chaos_and_secrets_decisions() -> None:
    release = evaluate_release_integrity(
        [ReleaseArtifact(artifact_id="wheel", signed_provenance=True, sbom_present=True, sbom_validated=True)]
    )
    assert release.release_allowed is True

    migration = evaluate_migration_readiness(
        MigrationEvidence(preflight_ok=True, dry_run_ok=False, rollback_rehearsal_ok=True)
    )
    assert migration.rollout_allowed is False

    budget = evaluate_error_budget(
        ErrorBudgetWindow(
            api_availability_consumed=0.9,
            order_pipeline_failure_consumed=0.4,
            stream_degradation_consumed=0.2,
            incident_latency_consumed=0.1,
        ),
        max_consumed=1.0,
    )
    assert budget.action == "throttle"

    chaos = evaluate_chaos_window(
        drills=[ChaosDrillResult(dependency="redis", detection_seconds=10, recovery_seconds=900, invariant_violations=0)],
        max_detection_seconds=60,
        max_recovery_seconds=600,
    )
    assert chaos.eligible_for_canary_live is False

    secrets = evaluate_secret_emergency(
        states=[SecretState(key_id="api", rotated_recently=False, expired=False, revocation_drill_minutes=40)],
        max_revocation_minutes=30,
    )
    assert secrets.allow_live_actions is False
    assert "rotation_overdue:api" in secrets.reason_codes
