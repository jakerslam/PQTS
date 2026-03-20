"""Production-readiness hardening contracts (PRDY family)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class RecoveryObjective:
    environment: str
    rto_minutes: int
    rpo_minutes: int


@dataclass(frozen=True)
class RecoveryMeasurement:
    environment: str
    measured_rto_minutes: int
    measured_rpo_minutes: int


@dataclass(frozen=True)
class RecoveryPostureDecision:
    promotion_eligible: bool
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class BackupManifest:
    artifact_id: str
    target_store: str
    checksum: str
    backup_ok: bool


@dataclass(frozen=True)
class RestoreDrillArtifact:
    artifact_id: str
    restore_minutes: int
    data_loss_minutes: int
    passed: bool


@dataclass(frozen=True)
class BackupRestoreDecision:
    policy_ok: bool
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class ReleaseArtifact:
    artifact_id: str
    signed_provenance: bool
    sbom_present: bool
    sbom_validated: bool


@dataclass(frozen=True)
class ReleaseIntegrityDecision:
    release_allowed: bool
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class MigrationEvidence:
    preflight_ok: bool
    dry_run_ok: bool
    rollback_rehearsal_ok: bool


@dataclass(frozen=True)
class MigrationDecision:
    rollout_allowed: bool
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class ErrorBudgetWindow:
    api_availability_consumed: float
    order_pipeline_failure_consumed: float
    stream_degradation_consumed: float
    incident_latency_consumed: float


@dataclass(frozen=True)
class ErrorBudgetDecision:
    action: str
    exhausted: bool
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class ChaosDrillResult:
    dependency: str
    detection_seconds: int
    recovery_seconds: int
    invariant_violations: int


@dataclass(frozen=True)
class ChaosWindowDecision:
    eligible_for_canary_live: bool
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class SecretState:
    key_id: str
    rotated_recently: bool
    expired: bool
    revocation_drill_minutes: int


@dataclass(frozen=True)
class SecretEmergencyDecision:
    allow_live_actions: bool
    reason_codes: Tuple[str, ...]


def evaluate_recovery_posture(
    *,
    objectives: List[RecoveryObjective],
    measurements: List[RecoveryMeasurement],
) -> RecoveryPostureDecision:
    measurement_by_env = {row.environment: row for row in measurements}
    reasons: List[str] = []
    for objective in objectives:
        measured = measurement_by_env.get(objective.environment)
        if measured is None:
            reasons.append(f"missing_measurement:{objective.environment}")
            continue
        if measured.measured_rto_minutes > objective.rto_minutes:
            reasons.append(f"rto_exceeded:{objective.environment}")
        if measured.measured_rpo_minutes > objective.rpo_minutes:
            reasons.append(f"rpo_exceeded:{objective.environment}")
    return RecoveryPostureDecision(
        promotion_eligible=not bool(reasons),
        reason_codes=tuple(sorted(set(reasons))),
    )


def evaluate_backup_restore(
    *,
    manifests: List[BackupManifest],
    drills: List[RestoreDrillArtifact],
    max_restore_minutes: int,
    max_data_loss_minutes: int,
) -> BackupRestoreDecision:
    reasons: List[str] = []
    drill_by_id = {row.artifact_id: row for row in drills}

    for manifest in manifests:
        if not manifest.backup_ok or not manifest.checksum:
            reasons.append(f"backup_integrity_failed:{manifest.artifact_id}")
        drill = drill_by_id.get(manifest.artifact_id)
        if drill is None:
            reasons.append(f"missing_restore_drill:{manifest.artifact_id}")
            continue
        if not drill.passed:
            reasons.append(f"restore_failed:{manifest.artifact_id}")
        if drill.restore_minutes > int(max_restore_minutes):
            reasons.append(f"restore_too_slow:{manifest.artifact_id}")
        if drill.data_loss_minutes > int(max_data_loss_minutes):
            reasons.append(f"data_loss_window_exceeded:{manifest.artifact_id}")

    return BackupRestoreDecision(policy_ok=not bool(reasons), reason_codes=tuple(sorted(set(reasons))))


def evaluate_release_integrity(artifacts: List[ReleaseArtifact]) -> ReleaseIntegrityDecision:
    reasons: List[str] = []
    for artifact in artifacts:
        if not artifact.signed_provenance:
            reasons.append(f"unsigned_artifact:{artifact.artifact_id}")
        if not artifact.sbom_present:
            reasons.append(f"missing_sbom:{artifact.artifact_id}")
        if not artifact.sbom_validated:
            reasons.append(f"sbom_validation_failed:{artifact.artifact_id}")

    return ReleaseIntegrityDecision(
        release_allowed=not bool(reasons),
        reason_codes=tuple(sorted(set(reasons))),
    )


def evaluate_migration_readiness(evidence: MigrationEvidence) -> MigrationDecision:
    reasons: List[str] = []
    if not evidence.preflight_ok:
        reasons.append("migration_preflight_failed")
    if not evidence.dry_run_ok:
        reasons.append("migration_dry_run_failed")
    if not evidence.rollback_rehearsal_ok:
        reasons.append("migration_rollback_rehearsal_missing")
    return MigrationDecision(rollout_allowed=not bool(reasons), reason_codes=tuple(sorted(set(reasons))))


def evaluate_error_budget(window: ErrorBudgetWindow, *, max_consumed: float = 1.0) -> ErrorBudgetDecision:
    reasons: List[str] = []
    action = "allow"
    consumed = {
        "api_availability": float(window.api_availability_consumed),
        "order_pipeline": float(window.order_pipeline_failure_consumed),
        "stream_health": float(window.stream_degradation_consumed),
        "incident_latency": float(window.incident_latency_consumed),
    }
    exhausted = False
    for key, value in consumed.items():
        if value > float(max_consumed):
            reasons.append(f"error_budget_exhausted:{key}")
            exhausted = True

    if exhausted:
        action = "safe_mode"
    elif any(value > (float(max_consumed) * 0.8) for value in consumed.values()):
        action = "throttle"
        reasons.append("error_budget_near_exhaustion")

    return ErrorBudgetDecision(action=action, exhausted=exhausted, reason_codes=tuple(sorted(set(reasons))))


def evaluate_chaos_window(
    *,
    drills: List[ChaosDrillResult],
    max_detection_seconds: int,
    max_recovery_seconds: int,
) -> ChaosWindowDecision:
    reasons: List[str] = []
    for drill in drills:
        if drill.detection_seconds > int(max_detection_seconds):
            reasons.append(f"slow_detection:{drill.dependency}")
        if drill.recovery_seconds > int(max_recovery_seconds):
            reasons.append(f"slow_recovery:{drill.dependency}")
        if drill.invariant_violations > 0:
            reasons.append(f"invariant_violation:{drill.dependency}")

    return ChaosWindowDecision(
        eligible_for_canary_live=not bool(reasons),
        reason_codes=tuple(sorted(set(reasons))),
    )


def evaluate_secret_emergency(
    *,
    states: List[SecretState],
    max_revocation_minutes: int,
) -> SecretEmergencyDecision:
    reasons: List[str] = []
    for state in states:
        if state.expired:
            reasons.append(f"expired_credential:{state.key_id}")
        if not state.rotated_recently:
            reasons.append(f"rotation_overdue:{state.key_id}")
        if state.revocation_drill_minutes > int(max_revocation_minutes):
            reasons.append(f"revocation_drill_too_slow:{state.key_id}")

    return SecretEmergencyDecision(
        allow_live_actions=not bool(reasons),
        reason_codes=tuple(sorted(set(reasons))),
    )
