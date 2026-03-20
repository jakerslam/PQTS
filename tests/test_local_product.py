from __future__ import annotations

import json
from pathlib import Path

from app.local_product import (
    ServiceSpec,
    build_bundle_manifest,
    build_support_bundle,
    evaluate_desktop_supervisor,
    evaluate_installer_continuity,
    evaluate_localhost_launch,
    evaluate_update_channel_transition,
    generate_first_run_config,
    write_runtime_status_artifact,
)


def _services() -> list[ServiceSpec]:
    return [
        ServiceSpec(
            name="api",
            command="run api",
            health_url="http://127.0.0.1:8100/health",
            url="http://127.0.0.1:8100",
            required_dependency="redis",
            required_port=8100,
        ),
        ServiceSpec(
            name="web",
            command="run web",
            health_url="http://127.0.0.1:3000/api/health",
            url="http://127.0.0.1:3000",
            required_dependency="node",
            required_port=3000,
        ),
    ]


def test_localhost_launch_fails_closed_with_diagnostics() -> None:
    summary = evaluate_localhost_launch(
        services=_services(),
        available_dependencies={"redis": False, "node": True},
        occupied_ports=[3000],
        health_by_service={"api": False, "web": True},
    )
    assert summary.ready is False
    assert "missing_dependency:redis" in summary.reason_codes
    assert "port_occupied:3000" in summary.reason_codes


def test_first_run_config_generates_safe_preview() -> None:
    config = generate_first_run_config(
        mode="paper",
        risk_profile="safe",
        workspace_path="/tmp/workspace",
        credentials={"api_key": "x"},
    )
    assert config.mode == "paper"
    assert config.policy_preview["default_capital_affecting_action"] == "hold"


def test_status_and_support_artifacts_are_machine_readable(tmp_path: Path) -> None:
    summary = evaluate_localhost_launch(
        services=_services(),
        available_dependencies={"redis": True, "node": True},
        occupied_ports=[],
        health_by_service={"api": True, "web": True},
    )
    status_path = write_runtime_status_artifact(
        path=str(tmp_path / "status.json"),
        state="ready",
        summary=summary,
    )
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["ready"] is True

    support_path = build_support_bundle(
        output_path=str(tmp_path / "support.json"),
        logs={"engine": "ok"},
        config={"api_key": "secret", "mode": "paper"},
        health={"api": "healthy"},
        version="0.1.5",
    )
    support = json.loads(support_path.read_text(encoding="utf-8"))
    assert support["config"]["api_key"] == "***REDACTED***"


def test_bundle_installer_update_and_desktop_decisions() -> None:
    manifest = build_bundle_manifest(
        bundle_id="pqts-local",
        version="0.1.5",
        os="darwin",
        arch="arm64",
        included_components=["api", "web", "worker"],
        verification_hash="abc123",
        signed=True,
    )
    assert manifest.signed is True

    continuity = evaluate_installer_continuity(
        from_version="0.1.4",
        to_version="0.1.5",
        migration_compatible=True,
        has_data_backup=False,
    )
    assert continuity.allowed is True

    update = evaluate_update_channel_transition(
        current_channel="stable",
        target_channel="beta",
        changes_governance_defaults=True,
        config_preserved=True,
        rollback_supported=True,
    )
    assert update.require_ack is True

    summary = evaluate_localhost_launch(
        services=_services(),
        available_dependencies={"redis": True, "node": True},
        occupied_ports=[],
        health_by_service={"api": True, "web": True},
    )
    desktop = evaluate_desktop_supervisor(
        launch_summary=summary,
        shutdown_clean=True,
        gated_actions_respected=True,
    )
    assert desktop.ready is True
