#!/usr/bin/env python3
"""Export the latest simulation leaderboard CSV as a static HTML page."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Iterable


def _latest_csv(reports_dir: Path, pattern: str) -> Path | None:
    rows = [path for path in reports_dir.glob(pattern) if path.is_file()]
    if not rows:
        return None
    return max(rows, key=lambda path: path.stat().st_mtime)


def _load_rows(csv_path: Path, limit: int) -> tuple[list[str], list[dict[str, str]]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = [dict(item) for item in reader]
    if limit > 0:
        rows = rows[:limit]
    return fields, rows


def _render_table(fields: Iterable[str], rows: list[dict[str, str]]) -> str:
    header = "".join(f"<th>{escape(field)}</th>" for field in fields)
    body_rows: list[str] = []
    for row in rows:
        cells = "".join(f"<td>{escape(str(row.get(field, '')))}</td>" for field in fields)
        body_rows.append(f"<tr>{cells}</tr>")
    return (
        "<table>"
        f"<thead><tr>{header}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


def _render_html(csv_path: Path | None, fields: list[str], rows: list[dict[str, str]]) -> str:
    now = datetime.now(UTC).isoformat()
    generated_from = str(csv_path) if csv_path else "none"

    if not csv_path:
        content = (
            "<p>No simulation leaderboard CSV was found yet.</p>"
            "<p>Run <code>make sim-suite</code> and republish this page.</p>"
        )
    elif not rows or not fields:
        content = f"<p>Leaderboard file exists but has no rows: <code>{escape(str(csv_path))}</code></p>"
    else:
        content = _render_table(fields, rows)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>PQTS Simulation Leaderboard</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0f172a;
      color: #e2e8f0;
      margin: 0;
      padding: 2rem;
    }}
    h1 {{
      margin-top: 0;
      font-size: 1.8rem;
    }}
    .meta {{
      color: #94a3b8;
      margin-bottom: 1rem;
      font-size: 0.95rem;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #111827;
      border: 1px solid #334155;
      border-radius: 8px;
      overflow: hidden;
    }}
    th, td {{
      padding: 0.55rem 0.7rem;
      border-bottom: 1px solid #1f2937;
      text-align: left;
      font-size: 0.92rem;
      white-space: nowrap;
    }}
    th {{
      background: #1e293b;
      color: #cbd5e1;
      font-weight: 600;
    }}
    tr:nth-child(even) {{
      background: #0b1220;
    }}
    code {{
      color: #93c5fd;
    }}
  </style>
</head>
<body>
  <h1>PQTS Simulation Leaderboard</h1>
  <div class="meta">Generated at: {escape(now)}</div>
  <div class="meta">Source: <code>{escape(generated_from)}</code></div>
  {content}
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports-dir", default="data/reports")
    parser.add_argument("--pattern", default="simulation_leaderboard_*.csv")
    parser.add_argument("--output-dir", default="site")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    reports_dir = Path(args.reports_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = _latest_csv(reports_dir, args.pattern) if reports_dir.exists() else None
    fields: list[str] = []
    rows: list[dict[str, str]] = []
    if csv_path:
        fields, rows = _load_rows(csv_path, limit=int(args.limit))

    html = _render_html(csv_path, fields, rows)
    out_path = output_dir / "index.html"
    out_path.write_text(html, encoding="utf-8")

    print(f"Wrote leaderboard page: {out_path}")
    if csv_path:
        print(f"Source CSV: {csv_path}")
    else:
        print("Source CSV: none found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
