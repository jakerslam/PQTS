from __future__ import annotations

from pathlib import Path

from tools.check_claim_evidence_links import evaluate_claim_evidence_links


def test_claim_evidence_links_pass_with_nearby_link(tmp_path: Path) -> None:
    file = tmp_path / "ok.md"
    file.write_text(
        "\n".join(
            [
                "Reference bundle delivered Sharpe 1.24 with max drawdown 3.1%.",
                "[Bundle report](results/2026-03-10_reference_market_making/README.md)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    assert evaluate_claim_evidence_links([file]) == []


def test_claim_evidence_links_fail_without_link(tmp_path: Path) -> None:
    file = tmp_path / "bad.md"
    file.write_text(
        "Precision reached 83% and fill rate 80% in this window.\n",
        encoding="utf-8",
    )
    errors = evaluate_claim_evidence_links([file])
    assert len(errors) == 1
    assert "claim appears without nearby evidence link" in errors[0]
