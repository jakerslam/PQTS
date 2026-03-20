from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import run_local_product_packaging


def test_launch_command_emits_status_artifact(tmp_path, monkeypatch) -> None:
    artifact = tmp_path / "status.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_local_product_packaging.py",
            "launch",
            "--status-artifact",
            str(artifact),
            "--redis-ok",
            "--api-ok",
            "--web-ok",
        ],
    )
    assert run_local_product_packaging.main() == 0
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["ready"] is True


def test_wizard_bundle_and_support_commands(tmp_path, monkeypatch) -> None:
    wizard_out = tmp_path / "wizard.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_local_product_packaging.py",
            "wizard",
            "--mode",
            "paper",
            "--risk-profile",
            "safe",
            "--workspace",
            str(tmp_path),
            "--out",
            str(wizard_out),
        ],
    )
    assert run_local_product_packaging.main() == 0
    wizard = json.loads(wizard_out.read_text(encoding="utf-8"))
    assert wizard["mode"] == "paper"

    bundle_out = tmp_path / "bundle.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_local_product_packaging.py",
            "bundle",
            "--bundle-id",
            "pqts-local",
            "--version",
            "0.1.5",
            "--os",
            "darwin",
            "--arch",
            "arm64",
            "--hash",
            "abc123",
            "--component",
            "api",
            "--component",
            "web",
            "--out",
            str(bundle_out),
        ],
    )
    assert run_local_product_packaging.main() == 0
    bundle = json.loads(bundle_out.read_text(encoding="utf-8"))
    assert bundle["bundle_id"] == "pqts-local"

    support_out = tmp_path / "support.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_local_product_packaging.py",
            "support",
            "--out",
            str(support_out),
            "--version",
            "0.1.5",
            "--config-json",
            '{"api_key":"secret","mode":"paper"}',
            "--health-json",
            '{"api":"healthy"}',
            "--logs-json",
            '{"engine":"ok"}',
        ],
    )
    assert run_local_product_packaging.main() == 0
    support = json.loads(support_out.read_text(encoding="utf-8"))
    assert support["config"]["api_key"] == "***REDACTED***"
