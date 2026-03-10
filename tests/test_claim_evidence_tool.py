from __future__ import annotations

from pathlib import Path

from tools.check_claim_evidence import evaluate_claim_evidence


def test_claim_evidence_passes_when_class_and_evidence_present(tmp_path: Path) -> None:
    file = tmp_path / "good.md"
    file.write_text(
        """
# Benchmark
Result class: diagnostic_only

## Command
```bash
python3 scripts/run_simulation_suite.py
```
""".strip()
        + "\n",
        encoding="utf-8",
    )
    assert evaluate_claim_evidence([file]) == []


def test_claim_evidence_fails_when_missing_markers(tmp_path: Path) -> None:
    file = tmp_path / "bad.md"
    file.write_text(
        """
# Benchmark
Quality improved from 0.1 to 0.2.
""".strip()
        + "\n",
        encoding="utf-8",
    )
    errors = evaluate_claim_evidence([file])
    assert len(errors) == 1
    assert "missing explicit claim classification" in errors[0]
