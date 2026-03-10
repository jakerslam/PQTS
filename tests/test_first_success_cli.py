from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import first_success_cli


def test_should_use_first_success_cli_routing() -> None:
    assert first_success_cli.should_use_first_success_cli([]) is True
    assert first_success_cli.should_use_first_success_cli(["--help"]) is True
    assert first_success_cli.should_use_first_success_cli(["demo"]) is True
    assert first_success_cli.should_use_first_success_cli(["doctor"]) is True
    assert first_success_cli.should_use_first_success_cli(["quickstart"]) is True
    assert first_success_cli.should_use_first_success_cli(["skills"]) is True
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


def test_skills_list_command_discovers_skill_packages(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    skill_path = tmp_path / "skills" / "alpha"
    skill_path.mkdir(parents=True, exist_ok=True)
    (skill_path / "SKILL.md").write_text("# Alpha Skill\n\nbody\n", encoding="utf-8")
    rc = first_success_cli.run_first_success_cli(
        ["skills", "list", "--skills-dir", str(tmp_path / "skills")]
    )
    assert rc == 0
    output = capsys.readouterr().out
    assert "alpha" in output
    assert "Alpha Skill" in output


def test_skills_urls_command_emits_raw_urls(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    skill_path = tmp_path / "skills" / "beta"
    skill_path.mkdir(parents=True, exist_ok=True)
    (skill_path / "SKILL.md").write_text("# Beta Skill\n", encoding="utf-8")
    rc = first_success_cli.run_first_success_cli(
        [
            "skills",
            "urls",
            "--skills-dir",
            str(tmp_path / "skills"),
            "--repo-base-url",
            "https://raw.githubusercontent.com/example/repo/main",
        ]
    )
    assert rc == 0
    output = capsys.readouterr().out
    assert "https://raw.githubusercontent.com/example/repo/main/skills/beta/SKILL.md" in output


def test_doctor_command_success(tmp_path: Path) -> None:
    config_path = tmp_path / "paper.yaml"
    config_path.write_text("mode: paper_trading\n", encoding="utf-8")
    rc = first_success_cli.run_first_success_cli(
        [
            "doctor",
            "--workspace",
            str(tmp_path),
            "--config",
            str(config_path),
            "--fix",
        ]
    )
    assert rc == 0
    assert (tmp_path / "data" / "reports").exists()


def test_quickstart_plan_and_execute(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path | None = None) -> int:
        calls.append(command)
        return 0

    monkeypatch.setattr(first_success_cli, "_run_command", fake_run)
    rc = first_success_cli.run_first_success_cli(
        [
            "quickstart",
            "--workspace",
            str(tmp_path),
            "--report-root",
            str(tmp_path / "reports"),
            "--execute",
        ]
    )
    assert rc == 0
    assert len(calls) == 4
    assert any("init" in " ".join(cmd) for cmd in calls)
    assert any("paper" in " ".join(cmd) for cmd in calls)


def test_strategy_and_risk_catalog_commands(capsys: pytest.CaptureFixture[str]) -> None:
    rc = first_success_cli.run_first_success_cli(["strategies", "list"])
    assert rc == 0
    assert "market_making" in capsys.readouterr().out

    rc = first_success_cli.run_first_success_cli(["strategies", "explain", "underdog_value"])
    assert rc == 0
    assert "Underdog Value" in capsys.readouterr().out

    rc = first_success_cli.run_first_success_cli(["risk", "list"])
    assert rc == 0
    assert "conservative" in capsys.readouterr().out

    rc = first_success_cli.run_first_success_cli(
        ["risk", "recommend", "--experience", "beginner", "--capital-usd", "1000"]
    )
    assert rc == 0
    assert "Profile: conservative" in capsys.readouterr().out


def test_status_commands_and_explain(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "simulation_suite_20260101.json").write_text("{}", encoding="utf-8")
    (reports_dir / "simulation_leaderboard_20260101.csv").write_text(
        "strategy,market,avg_quality_score\ntrend_following,crypto,0.88\n",
        encoding="utf-8",
    )
    gap_path = tmp_path / "SRS_GAP_BACKLOG.md"
    gap_path.write_text(
        "\n".join(
            [
                "# SRS Gap Backlog",
                "",
                "## P0",
                "",
                "Count: **0**",
                "",
                "## P1",
                "",
                "Count: **0**",
                "",
                "## P2",
                "",
                "Count: **10**",
            ]
        ),
        encoding="utf-8",
    )

    rc = first_success_cli.run_first_success_cli(["status", "reports", "--reports-dir", str(reports_dir)])
    assert rc == 0
    assert "simulation_suite_20260101.json" in capsys.readouterr().out

    rc = first_success_cli.run_first_success_cli(
        ["status", "leaderboard", "--reports-dir", str(reports_dir), "--top", "1"]
    )
    assert rc == 0
    assert "trend_following" in capsys.readouterr().out

    rc = first_success_cli.run_first_success_cli(
        ["status", "readiness", "--gap-backlog", str(gap_path)]
    )
    assert rc == 0
    assert "P0: 0" in capsys.readouterr().out

    rc = first_success_cli.run_first_success_cli(["explain", "block", "net_ev_non_positive"])
    assert rc == 0
    assert "Expected value" in capsys.readouterr().out


def test_notify_stdout_and_artifacts_latest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = first_success_cli.run_first_success_cli(["notify", "test", "--channel", "stdout"])
    assert rc == 0
    assert "[NOTIFY:stdout]" in capsys.readouterr().out

    artifacts_root = tmp_path / "data"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    (artifacts_root / "template_run_20260101.json").write_text("{}", encoding="utf-8")
    (artifacts_root / "template_run_diff_20260101.diff").write_text("", encoding="utf-8")
    rc = first_success_cli.run_first_success_cli(
        ["artifacts", "latest", "--root", str(artifacts_root), "--limit", "2"]
    )
    assert rc == 0
    output = capsys.readouterr().out
    assert "template_run_20260101.json" in output
