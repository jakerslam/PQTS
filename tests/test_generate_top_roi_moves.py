from __future__ import annotations

from pathlib import Path

from tools.generate_top_roi_moves import _parse_moves


def test_parse_moves_prioritizes_roi_impact_and_dependency(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    todo.write_text(
        "\n".join(
            [
                "## P0 Now",
                "- [ ] First root item (`ROI: very_high`, `Track: parity`, `Type: engineering`, `Impact: 10`, `Ref: A-1`)",
                "- [ ] Depends item (`ROI: very_high`, `Track: parity`, `Type: engineering`, `Impact: 10`, `Ref: A-2`, `Depends: A-1`)",
                "## P1 Next",
                "- [ ] Lower ROI item (`ROI: medium`, `Track: moat`, `Type: engineering`, `Impact: 10`, `Ref: A-3`)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    ranked = _parse_moves(todo)
    assert len(ranked) == 3
    assert ranked[0].title.startswith("First root item")
    assert ranked[1].title.startswith("Depends item")
    assert ranked[2].title.startswith("Lower ROI item")
    assert ranked[0].score > ranked[1].score > ranked[2].score


def test_parse_moves_preserves_non_metadata_backticks(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    todo.write_text(
        "\n".join(
            [
                "## P0 Now",
                "- [ ] Keep inline `code` in title (`ROI: high`, `Impact: 8`, `Ref: C-1`)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    ranked = _parse_moves(todo)
    assert ranked
    assert "`code`" in ranked[0].title
