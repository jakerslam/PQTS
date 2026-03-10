from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import first_success_cli


def test_should_use_first_success_cli_routing() -> None:
    assert first_success_cli.should_use_first_success_cli([]) is True
    assert first_success_cli.should_use_first_success_cli(["--help"]) is True
    assert first_success_cli.should_use_first_success_cli(["demo"]) is True
    assert first_success_cli.should_use_first_success_cli(["config/paper.yaml"]) is False


def test_init_creates_workspace_dirs_and_env(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("EXAMPLE=1\n", encoding="utf-8")
    rc = first_success_cli.run_first_success_cli(["init", "--workspace", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / ".env").exists()
    assert (tmp_path / "data" / "reports").exists()
    assert (tmp_path / "data" / "analytics").exists()
    assert (tmp_path / "data" / "tca" / "simulation").exists()
    assert (tmp_path / "results").exists()
    assert (tmp_path / "logs").exists()


def test_backtest_command_maps_template_and_invokes_suite(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(command: list[str], *, cwd: Path | None = None) -> int:
        captured["command"] = command
        captured["cwd"] = cwd
        return 0

    monkeypatch.setattr(first_success_cli, "_run_command", fake_run)
    rc = first_success_cli.run_first_success_cli(["backtest", "momentum"])
    assert rc == 0

    command = captured["command"]
    assert isinstance(command, list)
    assert "run_simulation_suite.py" in " ".join(command)
    assert "trend_following" in command


def test_backtest_writes_template_artifact(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_run(command: list[str], *, cwd: Path | None = None) -> int:
        return 0

    monkeypatch.setattr(first_success_cli, "_run_command", fake_run)
    rc = first_success_cli.run_first_success_cli(
        [
            "backtest",
            "momentum",
            "--out-dir",
            str(tmp_path),
        ]
    )
    assert rc == 0
    artifacts = sorted(tmp_path.glob("template_run_*.json"))
    diffs = sorted(tmp_path.glob("template_run_diff_*.diff"))
    assert artifacts
    assert diffs
    payload = json.loads(artifacts[-1].read_text(encoding="utf-8"))
    assert payload["template"] == "momentum"
    assert payload["resolved_strategy"] == "trend_following"


def test_paper_start_invokes_paper_campaign(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(command: list[str], *, cwd: Path | None = None) -> int:
        captured["command"] = command
        captured["cwd"] = cwd
        return 0

    monkeypatch.setattr(first_success_cli, "_run_command", fake_run)
    rc = first_success_cli.run_first_success_cli(["paper", "start", "--cycles", "3"])
    assert rc == 0

    command = captured["command"]
    assert isinstance(command, list)
    assert "run_paper_campaign.py" in " ".join(command)
    assert "--cycles" in command
    assert "3" in command


def test_paper_start_writes_template_artifact(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_run(command: list[str], *, cwd: Path | None = None) -> int:
        return 0

    monkeypatch.setattr(first_success_cli, "_run_command", fake_run)
    rc = first_success_cli.run_first_success_cli(
        [
            "paper",
            "start",
            "--out-dir",
            str(tmp_path),
        ]
    )
    assert rc == 0
    artifacts = sorted(tmp_path.glob("template_run_*.json"))
    assert artifacts
    payload = json.loads(artifacts[-1].read_text(encoding="utf-8"))
    assert payload["template"] == "paper_safe"
    assert payload["resolved_strategy"] == "campaign"


def test_first_success_cli_json_output_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / ".env.example").write_text("EXAMPLE=1\n", encoding="utf-8")
    rc = first_success_cli.run_first_success_cli(
        ["init", "--workspace", str(tmp_path), "--output", "json"]
    )
    assert rc == 0
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    payload = json.loads(lines[-1])
    assert payload["ok"] is True
    assert payload["command"] == "init"
    assert int(payload["return_code"]) == 0
    assert isinstance(payload["stdout"], list)


def test_first_success_cli_json_output_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(command: list[str], *, cwd: Path | None = None) -> int:
        return 9

    monkeypatch.setattr(first_success_cli, "_run_command", fake_run)
    rc = first_success_cli.run_first_success_cli(["demo", "--output", "json"])
    assert rc == 9
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    payload = json.loads(lines[-1])
    assert payload["ok"] is False
    assert payload["command"] == "demo"
    assert int(payload["return_code"]) == 9
    assert payload["error"] == "command_failed"
