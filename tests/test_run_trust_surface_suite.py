from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from tools import run_trust_surface_suite as module


def test_run_command_shapes_result(monkeypatch):
    def _fake_run(command, capture_output, text, check):  # noqa: ARG001
        return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    row = module.run_command(["python3", "dummy.py"])
    assert row["passed"] is True
    assert row["returncode"] == 0
    assert row["stdout"] == "ok"
    assert row["command"] == ["python3", "dummy.py"]


def test_run_suite_reports_failures(monkeypatch):
    calls = []

    def _fake_run(command, capture_output, text, check):  # noqa: ARG001
        calls.append(command)
        rc = 1 if "second.py" in command else 0
        return SimpleNamespace(returncode=rc, stdout="", stderr="")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    checks = (
        ("first", ["python3", "first.py"]),
        ("second", ["python3", "second.py"]),
    )
    report = module.run_suite(checks)
    assert report["passed"] is False
    assert report["failure_count"] == 1
    assert report["failures"] == ["second"]
    assert len(calls) == 2


def test_main_writes_report(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        module,
        "run_suite",
        lambda checks=module.CHECKS: {
            "generated_at_epoch": 123,
            "passed": True,
            "failure_count": 0,
            "failures": [],
            "results": {},
        },
    )
    out = tmp_path / "trust_surface_latest.json"
    import sys

    old = sys.argv
    sys.argv = ["run_trust_surface_suite.py", "--out", str(out)]
    try:
        rc = module.main()
    finally:
        sys.argv = old

    assert rc == 0
    assert out.exists()
