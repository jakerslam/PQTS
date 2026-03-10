from __future__ import annotations

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
