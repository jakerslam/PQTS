"""Local productization contracts for localhost/desktop packaging (PKG family)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    command: str
    health_url: str
    url: str
    required_dependency: str
    required_port: int


@dataclass(frozen=True)
class LaunchSummary:
    ready: bool
    startup_order: Tuple[str, ...]
    urls: Dict[str, str]
    health: Dict[str, str]
    reason_codes: Tuple[str, ...]
    recovery_guidance: Tuple[str, ...]


@dataclass(frozen=True)
class FirstRunConfig:
    mode: str
    risk_profile: str
    workspace_path: str
    credentials: Dict[str, str]
    policy_preview: Dict[str, Any]


@dataclass(frozen=True)
class BundleManifest:
    bundle_id: str
    version: str
    os: str
    arch: str
    included_components: Tuple[str, ...]
    verification_hash: str
    signed: bool


@dataclass(frozen=True)
class InstallerContinuityDecision:
    allowed: bool
    action: str
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class UpdateChannelDecision:
    action: str
    require_ack: bool
    reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class DesktopSupervisorState:
    ready: bool
    startup_state: str
    shutdown_state: str
    reason_codes: Tuple[str, ...]


def evaluate_localhost_launch(
    *,
    services: List[ServiceSpec],
    available_dependencies: Dict[str, bool],
    occupied_ports: List[int],
    health_by_service: Dict[str, bool],
) -> LaunchSummary:
    reasons: List[str] = []
    guidance: List[str] = []
    startup_order = tuple(row.name for row in services)
    urls = {row.name: row.url for row in services}
    health: Dict[str, str] = {}

    for row in services:
        if int(row.required_port) in {int(p) for p in occupied_ports}:
            reasons.append(f"port_occupied:{row.required_port}")
            guidance.append(f"free_port_{row.required_port}")
        if not bool(available_dependencies.get(row.required_dependency, False)):
            reasons.append(f"missing_dependency:{row.required_dependency}")
            guidance.append(f"install_or_start_{row.required_dependency}")

        healthy = bool(health_by_service.get(row.name, False))
        health[row.name] = "healthy" if healthy else "degraded"
        if not healthy:
            reasons.append(f"healthcheck_failed:{row.name}")
            guidance.append(f"inspect_health:{row.health_url}")

    return LaunchSummary(
        ready=not bool(reasons),
        startup_order=startup_order,
        urls=urls,
        health=health,
        reason_codes=tuple(sorted(set(reasons))),
        recovery_guidance=tuple(sorted(set(guidance))),
    )


def generate_first_run_config(
    *,
    mode: str,
    risk_profile: str,
    workspace_path: str,
    credentials: Dict[str, str] | None,
) -> FirstRunConfig:
    mode_token = str(mode).strip().lower()
    if mode_token not in {"paper", "shadow", "canary", "live"}:
        raise ValueError("mode must be one of: paper, shadow, canary, live")

    risk_token = str(risk_profile).strip().lower()
    if risk_token not in {"safe", "balanced", "aggressive"}:
        raise ValueError("risk_profile must be one of: safe, balanced, aggressive")

    workspace = str(workspace_path).strip()
    if not workspace:
        raise ValueError("workspace_path is required")

    creds = {str(k): str(v) for k, v in (credentials or {}).items() if str(v).strip()}
    policy_preview = {
        "mode": mode_token,
        "risk_profile": risk_token,
        "edge_gate": "enabled",
        "live_orders_allowed": mode_token == "live",
        "default_capital_affecting_action": "hold" if mode_token != "live" else "submit",
    }
    return FirstRunConfig(
        mode=mode_token,
        risk_profile=risk_token,
        workspace_path=workspace,
        credentials=creds,
        policy_preview=policy_preview,
    )


def write_runtime_status_artifact(
    *,
    path: str,
    state: str,
    summary: LaunchSummary,
) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "state": str(state),
        "ready": bool(summary.ready),
        "startup_order": list(summary.startup_order),
        "urls": dict(summary.urls),
        "health": dict(summary.health),
        "reason_codes": list(summary.reason_codes),
        "recovery_guidance": list(summary.recovery_guidance),
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def build_bundle_manifest(
    *,
    bundle_id: str,
    version: str,
    os: str,
    arch: str,
    included_components: List[str],
    verification_hash: str,
    signed: bool,
) -> BundleManifest:
    if not verification_hash:
        raise ValueError("verification_hash is required")
    return BundleManifest(
        bundle_id=str(bundle_id).strip(),
        version=str(version).strip(),
        os=str(os).strip(),
        arch=str(arch).strip(),
        included_components=tuple(sorted(set(str(item).strip() for item in included_components if str(item).strip()))),
        verification_hash=str(verification_hash).strip(),
        signed=bool(signed),
    )


def evaluate_installer_continuity(
    *,
    from_version: str,
    to_version: str,
    migration_compatible: bool,
    has_data_backup: bool,
) -> InstallerContinuityDecision:
    reasons: List[str] = []
    action = "proceed"
    if not migration_compatible:
        reasons.append("migration_incompatible")
        action = "block"
    if not has_data_backup:
        reasons.append("missing_data_backup")
        action = "warn_and_backup"
        if "migration_incompatible" in reasons:
            action = "block"
    return InstallerContinuityDecision(
        allowed=action != "block",
        action=action,
        reason_codes=tuple(sorted(set(reasons))),
    )


def evaluate_update_channel_transition(
    *,
    current_channel: str,
    target_channel: str,
    changes_governance_defaults: bool,
    config_preserved: bool,
    rollback_supported: bool,
) -> UpdateChannelDecision:
    reasons: List[str] = []
    action = "allow"
    if not config_preserved:
        reasons.append("config_not_preserved")
        action = "block"
    if not rollback_supported:
        reasons.append("rollback_not_supported")
        action = "block"
    require_ack = bool(changes_governance_defaults)
    if require_ack:
        reasons.append("governance_defaults_changed")
    return UpdateChannelDecision(
        action=action,
        require_ack=require_ack,
        reason_codes=tuple(sorted(set(reasons))),
    )


def evaluate_desktop_supervisor(
    *,
    launch_summary: LaunchSummary,
    shutdown_clean: bool,
    gated_actions_respected: bool,
) -> DesktopSupervisorState:
    reasons: List[str] = []
    if not launch_summary.ready:
        reasons.append("launch_not_ready")
    if not shutdown_clean:
        reasons.append("shutdown_not_clean")
    if not gated_actions_respected:
        reasons.append("policy_gates_violated")
    return DesktopSupervisorState(
        ready=not bool(reasons),
        startup_state="ready" if launch_summary.ready else "degraded",
        shutdown_state="clean" if shutdown_clean else "unclean",
        reason_codes=tuple(sorted(set(reasons))),
    )


def build_support_bundle(
    *,
    output_path: str,
    logs: Dict[str, str],
    config: Dict[str, Any],
    health: Dict[str, Any],
    version: str,
) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    redacted_config: Dict[str, Any] = {}
    for key, value in config.items():
        token = str(key).lower()
        if any(secret in token for secret in ("secret", "key", "token", "password")):
            redacted_config[key] = "***REDACTED***"
        else:
            redacted_config[key] = value

    payload = {
        "version": str(version),
        "logs": dict(logs),
        "health": dict(health),
        "config": redacted_config,
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out
