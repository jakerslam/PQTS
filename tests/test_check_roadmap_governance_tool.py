from __future__ import annotations

import json
from pathlib import Path

from tools import check_roadmap_governance


def test_check_roadmap_governance_passes_with_recent_review(tmp_path: Path, monkeypatch) -> None:
    todo = tmp_path / "TODO.md"
    todo.write_text(
        """
- [x] parity done (`Track: parity`, `Ref: A-1`)
- [ ] moat open (`Track: moat`, `Ref: A-2`)
- [ ] parity open (`Track: parity`, `Ref: A-3`)
- [ ] moat open two (`Track: moat`, `Ref: A-4`)
""".strip()
        + "\n",
        encoding="utf-8",
    )
    review = tmp_path / "REVIEW.md"
    review.write_text("Last updated: 2026-03-10\n", encoding="utf-8")
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps(
            {
                "min_moat_share_after_parity_p0": 0.5,
                "quarterly_review": {
                    "max_review_age_days": 120,
                    "review_file": str(review),
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "check_roadmap_governance.py",
            "--todo",
            str(todo),
            "--policy",
            str(policy),
            "--today",
            "2026-03-10",
        ],
    )
    assert check_roadmap_governance.main() == 0


def test_check_roadmap_governance_fails_when_review_missing(tmp_path: Path, monkeypatch) -> None:
    todo = tmp_path / "TODO.md"
    todo.write_text("- [ ] parity open (`Track: parity`, `Ref: A-1`)\n", encoding="utf-8")
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps(
            {
                "min_moat_share_after_parity_p0": 0.1,
                "quarterly_review": {
                    "max_review_age_days": 30,
                    "review_file": str(tmp_path / "missing.md"),
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "check_roadmap_governance.py",
            "--todo",
            str(todo),
            "--policy",
            str(policy),
            "--today",
            "2026-03-10",
        ],
    )
    assert check_roadmap_governance.main() == 2
