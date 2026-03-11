#!/usr/bin/env python3
"""Generate a ranked Top-N ROI move list from docs/TODO.md.

This turns the active TODO backlog into a dependency-aware execution slice so
operators can consistently pick the next highest leverage work.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_ITEM_RE = re.compile(r"^\s*-\s*\[\s*\]\s*(.+)$")
_META_RE = re.compile(r"`([^`]+)`")
_FIELD_RE = re.compile(r"^\s*([A-Za-z_ ]+)\s*:\s*(.+?)\s*$")

_ROI_WEIGHT = {
    "very_high": 4.0,
    "high": 3.0,
    "medium": 2.0,
    "low": 1.0,
}

_TRACK_BONUS = {
    "parity": 0.20,
    "moat": 0.10,
}


@dataclass(frozen=True)
class Move:
    rank: int
    score: float
    title: str
    roi: str
    impact: int
    track: str
    item_type: str
    refs: str
    depends: str
    section: str
    line_no: int


def _iter_lines(path: Path) -> Iterable[tuple[int, str]]:
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        yield idx, line.rstrip("\n")


def _extract_fields(item_text: str) -> tuple[str, dict[str, str]]:
    fields: dict[str, str] = {}
    def _replace(match_obj: re.Match[str]) -> str:
        raw_meta = match_obj.group(1)
        field_match = _FIELD_RE.match(raw_meta)
        if not field_match:
            return match_obj.group(0)
        key = field_match.group(1).strip().lower().replace(" ", "_")
        value = field_match.group(2).strip()
        fields[key] = value
        return ""

    title = _META_RE.sub(_replace, item_text).strip()
    title = re.sub(r"\(\s*(?:,\s*)+\)", "", title)
    title = re.sub(r"\(\s*\)", "", title)
    title = re.sub(r"\s{2,}", " ", title).strip()
    title = title.rstrip(" ,;")
    return title, fields


def _score(fields: dict[str, str], section: str) -> float:
    roi = fields.get("roi", "medium").strip().lower()
    roi_weight = _ROI_WEIGHT.get(roi, _ROI_WEIGHT["medium"])
    impact = int(fields.get("impact", "5"))
    depends = fields.get("depends", "")
    dep_count = len([x for x in re.split(r"[,\s]+", depends) if x.strip() and "-" in x])
    track = fields.get("track", "").strip().lower()
    track_bonus = _TRACK_BONUS.get(track, 0.0)
    section_bonus = 0.0
    if section.startswith("P0") or "P0 " in section:
        section_bonus += 0.35
    if "Now" in section:
        section_bonus += 0.15
    return (roi_weight * 100.0) + (impact * 8.0) + (track_bonus * 100.0) + (
        section_bonus * 100.0
    ) - (dep_count * 6.0)


def _parse_moves(path: Path) -> list[Move]:
    current_section = "Unsectioned"
    parsed: list[tuple[float, str, dict[str, str], str, int]] = []
    for line_no, line in _iter_lines(path):
        if line.startswith("## "):
            current_section = line[3:].strip()
            continue
        if line.startswith("### "):
            current_section = line[4:].strip()
            continue
        match = _ITEM_RE.match(line)
        if not match:
            continue
        title, fields = _extract_fields(match.group(1).strip())
        score = _score(fields, current_section)
        parsed.append((score, title, fields, current_section, line_no))

    parsed.sort(key=lambda item: (-item[0], item[4], item[1].lower()))
    moves: list[Move] = []
    for idx, (score, title, fields, section, line_no) in enumerate(parsed, start=1):
        moves.append(
            Move(
                rank=idx,
                score=round(score, 2),
                title=title,
                roi=fields.get("roi", "medium"),
                impact=int(fields.get("impact", "5")),
                track=fields.get("track", "parity"),
                item_type=fields.get("type", "engineering"),
                refs=fields.get("ref", ""),
                depends=fields.get("depends", ""),
                section=section,
                line_no=line_no,
            )
        )
    return moves


def _render_markdown(moves: list[Move], *, todo_path: Path) -> str:
    lines = [
        "# Top ROI Moves (Auto-Generated)",
        "",
        "Generated from open TODO items in `docs/TODO.md`.",
        "",
        f"- Source: `{todo_path}`",
        f"- Total ranked open items: `{len(moves)}`",
        "",
        "| Rank | Score | ROI | Impact | Track | Type | Ref | Depends | Section | Move |",
        "|---:|---:|---|---:|---|---|---|---|---|---|",
    ]
    for move in moves:
        lines.append(
            "| "
            f"{move.rank} | {move.score:.2f} | {move.roi} | {move.impact} | {move.track} | {move.item_type} | "
            f"{move.refs or '-'} | {move.depends or '-'} | {move.section} | {move.title} |"
        )
    lines.append("")
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--todo", default="docs/TODO.md")
    parser.add_argument("--top", type=int, default=100)
    parser.add_argument("--md-out", default="docs/TOP_100_ROI_MOVES.md")
    parser.add_argument("--json-out", default="docs/TOP_100_ROI_MOVES.json")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    todo_path = Path(args.todo)
    md_out = Path(args.md_out)
    json_out = Path(args.json_out)
    top_n = max(int(args.top), 1)

    moves = _parse_moves(todo_path)[:top_n]
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.parent.mkdir(parents=True, exist_ok=True)

    md_out.write_text(_render_markdown(moves, todo_path=todo_path), encoding="utf-8")
    json_out.write_text(
        json.dumps([move.__dict__ for move in moves], indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "todo": str(todo_path),
                "top": top_n,
                "md_out": str(md_out),
                "json_out": str(json_out),
                "count": len(moves),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
