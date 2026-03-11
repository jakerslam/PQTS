from __future__ import annotations

import json
from pathlib import Path

from tools.generate_full_srs_closure_artifacts import _extract_families, _write_defaults, _write_map


def test_extract_families_reads_02l_assimilation_rows() -> None:
    todo_text = "\n".join(
        [
            "## 02l. Full SRS Assimilation Closure (2026-03-10)",
            "- [ ] Assimilate AL requirement family (`Ref: AL-1, AL-2`, `Evidence: x`)",
            "- [x] Assimilate NS requirement family (`Ref: NS-1`, `Evidence: y`)",
            "## 03. Human-Only",
            "- [ ] Ignore",
        ]
    )
    families = _extract_families(todo_text)
    assert list(families.keys()) == ["AL", "NS"]
    assert families["AL"] == ["AL-1", "AL-2"]
    assert families["NS"] == ["NS-1"]


def test_write_defaults_and_map(tmp_path: Path) -> None:
    families = {"AL": ["AL-1", "AL-2"], "NS": ["NS-1"]}
    defaults_path = tmp_path / "defaults.json"
    map_path = tmp_path / "map.md"

    _write_defaults(defaults_path, families)  # type: ignore[arg-type]
    _write_map(map_path, families)  # type: ignore[arg-type]

    payload = json.loads(defaults_path.read_text(encoding="utf-8"))
    assert payload["families"]["AL"]["refs"] == ["AL-1", "AL-2"]
    assert payload["families"]["AL"]["controls"]["fail_closed"] is True
    assert "## AL Family" in map_path.read_text(encoding="utf-8")
