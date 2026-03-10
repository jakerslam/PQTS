from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "examples" / "wallet_modes" / "run_example.py"


def _run(mode: str) -> dict:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--mode", mode, "--dry-run", "--output", "json"],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    assert lines
    return json.loads(lines[-1])


def test_wallet_examples_smoke_for_all_modes() -> None:
    for mode in ("eoa", "proxy", "safe"):
        payload = _run(mode)
        assert payload["mode"] == mode
        assert payload["dry_run"] is True
        assert isinstance(payload["required_env"], list)
