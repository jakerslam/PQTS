"""Monthly benchmark report generation for reproducible results bundles."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import statistics
from typing import Any, Dict, List, Mapping, Sequence, Tuple


_MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")


@dataclass(frozen=True)
class AttributionRow:
    """Per market/strategy attribution row."""

    market: str
    strategy: str
    runs: int
    total_pnl: float
    avg_quality_score: float
    avg_fill_rate: float
    avg_reject_rate: float
    sharpe: float
    max_drawdown: float


@dataclass(frozen=True)
class MonthlyReport:
    """Serializable monthly report payload."""

    month: str
    generated_at: str
    bundle_count: int
    scenario_count: int
    starting_equity: float
    ending_equity: float
    total_pnl: float
    sharpe: float
    max_drawdown: float
    equity_curve: List[float]
    attribution_rows: List[AttributionRow]

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["attribution_rows"] = [asdict(row) for row in self.attribution_rows]
        return payload


@dataclass(frozen=True)
class MonthlyReportArtifacts:
    """Filesystem outputs produced by monthly report generation."""

    report: MonthlyReport
    json_path: Path
    html_path: Path
    pdf_path: Path
    equity_curve_svg_path: Path


def _validate_month(month: str) -> str:
    value = str(month).strip()
    if not _MONTH_PATTERN.match(value):
        raise ValueError(f"invalid month format: {month!r}; expected YYYY-MM")
    return value


def discover_month_bundles(results_dir: str | Path, month: str) -> List[Path]:
    """Discover results bundle directories for the requested month."""
    month = _validate_month(month)
    root = Path(results_dir)
    if not root.exists():
        return []

    bundles: List[Path] = []
    prefix = f"{month}-"
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith(prefix):
            bundles.append(child)
    return bundles


def _latest_suite_payload(bundle_dir: Path) -> Mapping[str, Any] | None:
    candidates = sorted(bundle_dir.glob("simulation_suite_*.json"))
    if not candidates:
        return None
    return json.loads(candidates[-1].read_text(encoding="utf-8"))


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _result_pnl(result: Mapping[str, Any]) -> float:
    """Resolve per-run pnl from explicit fields or deterministic fallback."""
    for key in ("pnl", "realized_pnl", "realized_pnl_usd", "pnl_usd"):
        if key in result:
            return _safe_float(result.get(key))

    quality = _safe_float(result.get("quality_score", 0.0))
    scenario = result.get("scenario")
    if isinstance(scenario, Mapping):
        notional = _safe_float(scenario.get("notional_usd", 0.0))
        if notional > 0:
            return quality * notional
    return quality


def _compute_sharpe(returns: Sequence[float]) -> float:
    values = [float(x) for x in returns]
    if len(values) < 2:
        return 0.0
    stdev = statistics.pstdev(values)
    if stdev <= 1e-12:
        return 0.0
    mean = statistics.fmean(values)
    return float((mean / stdev) * math.sqrt(252.0))


def _compute_max_drawdown(equity_curve: Sequence[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = float(equity_curve[0])
    max_dd = 0.0
    for point in equity_curve:
        value = float(point)
        if value > peak:
            peak = value
        if peak > 0:
            drawdown = (peak - value) / peak
            if drawdown > max_dd:
                max_dd = drawdown
    return float(max_dd)


def build_monthly_report(
    *,
    results_dir: str | Path,
    month: str,
    starting_equity: float = 10_000.0,
) -> MonthlyReport:
    """Aggregate monthly result bundles into one benchmark report payload."""
    month = _validate_month(month)
    bundles = discover_month_bundles(results_dir, month)

    scenario_count = 0
    equity_curve: List[float] = [float(starting_equity)]
    portfolio_returns: List[float] = []

    agg: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for bundle in bundles:
        payload = _latest_suite_payload(bundle)
        if not payload:
            continue

        results = payload.get("results")
        if not isinstance(results, list):
            results = []
        leaderboard = payload.get("leaderboard")
        if not isinstance(leaderboard, list):
            leaderboard = []

        if results:
            for result in results:
                if not isinstance(result, Mapping):
                    continue
                scenario = result.get("scenario")
                scenario = scenario if isinstance(scenario, Mapping) else {}
                market = str(scenario.get("market") or "unknown")
                strategy = str(scenario.get("strategy") or "unknown")

                pnl = _result_pnl(result)
                prev_equity = equity_curve[-1]
                new_equity = prev_equity + pnl
                equity_curve.append(float(new_equity))
                if prev_equity != 0:
                    portfolio_returns.append(float(pnl / prev_equity))
                scenario_count += 1

                submitted = max(1.0, _safe_float(result.get("submitted", 0.0)))
                filled = _safe_float(result.get("filled", 0.0))
                reject_rate = _safe_float(result.get("reject_rate", 0.0))
                quality = _safe_float(result.get("quality_score", 0.0))
                fill_rate = filled / submitted

                bucket = agg.setdefault(
                    (market, strategy),
                    {
                        "runs": 0,
                        "total_pnl": 0.0,
                        "sum_quality": 0.0,
                        "sum_fill": 0.0,
                        "sum_reject": 0.0,
                        "returns": [],
                        "equity": [float(starting_equity)],
                    },
                )
                bucket["runs"] += 1
                bucket["total_pnl"] += pnl
                bucket["sum_quality"] += quality
                bucket["sum_fill"] += fill_rate
                bucket["sum_reject"] += reject_rate
                bucket["returns"].append(float(pnl / starting_equity) if starting_equity else 0.0)
                bucket["equity"].append(float(bucket["equity"][-1] + pnl))
            continue

        for row in leaderboard:
            if not isinstance(row, Mapping):
                continue
            market = str(row.get("market") or "unknown")
            strategy = str(row.get("strategy") or "unknown")
            runs = max(1, int(_safe_float(row.get("runs", 1))))
            quality = _safe_float(row.get("avg_quality_score", 0.0))
            fill_rate = _safe_float(row.get("avg_fill_rate", 0.0))
            reject_rate = _safe_float(row.get("avg_reject_rate", 0.0))

            bucket = agg.setdefault(
                (market, strategy),
                {
                    "runs": 0,
                    "total_pnl": 0.0,
                    "sum_quality": 0.0,
                    "sum_fill": 0.0,
                    "sum_reject": 0.0,
                    "returns": [],
                    "equity": [float(starting_equity)],
                },
            )
            bucket["runs"] += runs
            bucket["sum_quality"] += quality * runs
            bucket["sum_fill"] += fill_rate * runs
            bucket["sum_reject"] += reject_rate * runs
            scenario_count += runs

    attribution_rows: List[AttributionRow] = []
    for (market, strategy), stats in sorted(agg.items(), key=lambda item: item[0]):
        runs = int(stats["runs"])
        if runs <= 0:
            continue
        attribution_rows.append(
            AttributionRow(
                market=market,
                strategy=strategy,
                runs=runs,
                total_pnl=float(stats["total_pnl"]),
                avg_quality_score=float(stats["sum_quality"] / runs),
                avg_fill_rate=float(stats["sum_fill"] / runs),
                avg_reject_rate=float(stats["sum_reject"] / runs),
                sharpe=_compute_sharpe(stats["returns"]),
                max_drawdown=_compute_max_drawdown(stats["equity"]),
            )
        )

    ending_equity = float(equity_curve[-1]) if equity_curve else float(starting_equity)
    total_pnl = ending_equity - float(starting_equity)

    return MonthlyReport(
        month=month,
        generated_at=datetime.now(timezone.utc).isoformat(),
        bundle_count=len(bundles),
        scenario_count=int(scenario_count),
        starting_equity=float(starting_equity),
        ending_equity=ending_equity,
        total_pnl=float(total_pnl),
        sharpe=_compute_sharpe(portfolio_returns),
        max_drawdown=_compute_max_drawdown(equity_curve),
        equity_curve=[float(point) for point in equity_curve],
        attribution_rows=sorted(
            attribution_rows,
            key=lambda row: (row.total_pnl, row.avg_quality_score),
            reverse=True,
        ),
    )


def render_equity_curve_svg(
    *, report: MonthlyReport, output_path: str | Path, width: int = 960, height: int = 320
) -> Path:
    """Render a simple deterministic SVG equity curve chart."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    points = list(report.equity_curve)
    if len(points) < 2:
        points = [report.starting_equity, report.ending_equity]

    pad_left = 48
    pad_right = 24
    pad_top = 24
    pad_bottom = 40
    inner_w = max(1, width - pad_left - pad_right)
    inner_h = max(1, height - pad_top - pad_bottom)

    min_y = min(points)
    max_y = max(points)
    if abs(max_y - min_y) < 1e-9:
        max_y = min_y + 1.0

    def scale_x(idx: int) -> float:
        if len(points) == 1:
            return float(pad_left)
        return float(pad_left + (idx / (len(points) - 1)) * inner_w)

    def scale_y(value: float) -> float:
        ratio = (value - min_y) / (max_y - min_y)
        return float(pad_top + (1.0 - ratio) * inner_h)

    polyline = " ".join(f"{scale_x(i):.2f},{scale_y(v):.2f}" for i, v in enumerate(points))
    y_start = scale_y(points[0])
    y_end = scale_y(points[-1])

    svg = f"""<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{width}\" height=\"{height}\" viewBox=\"0 0 {width} {height}\" role=\"img\" aria-label=\"PQTS monthly equity curve\">\n  <rect x=\"0\" y=\"0\" width=\"{width}\" height=\"{height}\" fill=\"#0f172a\"/>\n  <line x1=\"{pad_left}\" y1=\"{pad_top + inner_h}\" x2=\"{pad_left + inner_w}\" y2=\"{pad_top + inner_h}\" stroke=\"#334155\" stroke-width=\"1\"/>\n  <line x1=\"{pad_left}\" y1=\"{pad_top}\" x2=\"{pad_left}\" y2=\"{pad_top + inner_h}\" stroke=\"#334155\" stroke-width=\"1\"/>\n  <polyline points=\"{polyline}\" fill=\"none\" stroke=\"#22d3ee\" stroke-width=\"2.5\"/>\n  <circle cx=\"{scale_x(0):.2f}\" cy=\"{y_start:.2f}\" r=\"3\" fill=\"#38bdf8\"/>\n  <circle cx=\"{scale_x(len(points) - 1):.2f}\" cy=\"{y_end:.2f}\" r=\"3\" fill=\"#34d399\"/>\n  <text x=\"{pad_left}\" y=\"{height - 12}\" fill=\"#94a3b8\" font-family=\"Menlo, Consolas, monospace\" font-size=\"12\">Start: {report.starting_equity:.2f}</text>\n  <text x=\"{width - 250}\" y=\"{height - 12}\" fill=\"#94a3b8\" font-family=\"Menlo, Consolas, monospace\" font-size=\"12\">End: {report.ending_equity:.2f}</text>\n</svg>\n"""
    path.write_text(svg, encoding="utf-8")
    return path


def _escape_html(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def render_monthly_report_html(
    *, report: MonthlyReport, output_path: str | Path, equity_curve_svg_name: str
) -> Path:
    """Render the monthly benchmark report as HTML."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    row_html = "\n".join(
        (
            f"<tr><td>{_escape_html(row.market)}</td>"
            f"<td>{_escape_html(row.strategy)}</td>"
            f"<td>{row.runs}</td>"
            f"<td>{row.total_pnl:.2f}</td>"
            f"<td>{row.avg_quality_score:.4f}</td>"
            f"<td>{row.avg_fill_rate:.4f}</td>"
            f"<td>{row.avg_reject_rate:.4f}</td>"
            f"<td>{row.sharpe:.4f}</td>"
            f"<td>{row.max_drawdown:.4f}</td></tr>"
        )
        for row in report.attribution_rows
    )

    html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>PQTS Monthly Report {report.month}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f8fafc;
      --surface: #ffffff;
      --ink: #0f172a;
      --muted: #475569;
      --border: #cbd5e1;
      --accent: #0ea5e9;
    }}
    body {{
      margin: 0;
      padding: 24px;
      background: radial-gradient(circle at top right, #e2e8f0 0%, var(--bg) 55%);
      color: var(--ink);
      font-family: 'IBM Plex Sans', 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }}
    .card {{
      max-width: 1100px;
      margin: 0 auto;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 20px 24px;
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
    }}
    h1, h2 {{ margin: 0 0 12px; }}
    h1 {{ font-size: 28px; }}
    h2 {{ font-size: 20px; margin-top: 20px; }}
    .meta {{ color: var(--muted); margin-bottom: 16px; }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }}
    .kpi {{
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px;
      background: #f8fafc;
    }}
    .kpi .label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }}
    .kpi .value {{ font-size: 20px; font-weight: 700; color: var(--ink); }}
    img {{ width: 100%; border: 1px solid var(--border); border-radius: 10px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 14px; }}
    th, td {{ border: 1px solid var(--border); padding: 8px; text-align: right; }}
    th:first-child, td:first-child, th:nth-child(2), td:nth-child(2) {{ text-align: left; }}
    th {{ background: #e2e8f0; }}
    .footer {{ color: var(--muted); margin-top: 14px; font-size: 12px; }}
    @media (max-width: 720px) {{
      body {{ padding: 12px; }}
      .card {{ padding: 14px; }}
      table {{ display: block; overflow-x: auto; }}
    }}
  </style>
</head>
<body>
  <main class=\"card\">
    <h1>PQTS Monthly Benchmark Report - {report.month}</h1>
    <p class=\"meta\">Generated at {report.generated_at}</p>

    <section class=\"kpi-grid\">
      <div class=\"kpi\"><div class=\"label\">Bundles</div><div class=\"value\">{report.bundle_count}</div></div>
      <div class=\"kpi\"><div class=\"label\">Scenarios</div><div class=\"value\">{report.scenario_count}</div></div>
      <div class=\"kpi\"><div class=\"label\">Total PnL</div><div class=\"value\">{report.total_pnl:.2f}</div></div>
      <div class=\"kpi\"><div class=\"label\">Sharpe</div><div class=\"value\">{report.sharpe:.4f}</div></div>
      <div class=\"kpi\"><div class=\"label\">Max Drawdown</div><div class=\"value\">{report.max_drawdown:.4f}</div></div>
    </section>

    <section>
      <h2>Equity Curve</h2>
      <img src=\"{_escape_html(equity_curve_svg_name)}\" alt=\"Monthly equity curve\" />
    </section>

    <section>
      <h2>Attribution Table</h2>
      <table>
        <thead>
          <tr>
            <th>Market</th>
            <th>Strategy</th>
            <th>Runs</th>
            <th>Total PnL</th>
            <th>Avg Quality</th>
            <th>Avg Fill</th>
            <th>Avg Reject</th>
            <th>Sharpe</th>
            <th>Max DD</th>
          </tr>
        </thead>
        <tbody>
          {row_html}
        </tbody>
      </table>
    </section>

    <p class=\"footer\">Source bundles: {report.bundle_count} under results/{report.month}-*</p>
  </main>
</body>
</html>
"""

    path.write_text(html, encoding="utf-8")
    return path


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_text_pdf(*, lines: Sequence[str], output_path: str | Path) -> Path:
    """Write a minimal single-page text PDF without external dependencies."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    safe_lines = [_escape_pdf_text(str(line)) for line in lines]
    text_ops: List[str] = ["BT", "/F1 10 Tf", "40 760 Td"]
    first = True
    for line in safe_lines[:48]:
        if not first:
            text_ops.append("0 -14 Td")
        text_ops.append(f"({line}) Tj")
        first = False
    text_ops.append("ET")
    stream_data = "\n".join(text_ops).encode("latin-1", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n" % len(stream_data) + stream_data + b"\nendstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{idx} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("ascii")
    )

    path.write_bytes(bytes(pdf))
    return path


def render_monthly_report_pdf(*, report: MonthlyReport, output_path: str | Path) -> Path:
    """Render a text-focused PDF companion for the monthly benchmark report."""
    lines = [
        f"PQTS Monthly Benchmark Report - {report.month}",
        f"Generated at: {report.generated_at}",
        f"Bundles: {report.bundle_count}",
        f"Scenarios: {report.scenario_count}",
        f"Starting equity: {report.starting_equity:.2f}",
        f"Ending equity: {report.ending_equity:.2f}",
        f"Total PnL: {report.total_pnl:.2f}",
        f"Sharpe: {report.sharpe:.4f}",
        f"Max drawdown: {report.max_drawdown:.4f}",
        "",
        "Attribution:",
    ]
    for row in report.attribution_rows[:30]:
        lines.append(
            (
                f"{row.market}/{row.strategy} runs={row.runs} pnl={row.total_pnl:.2f} "
                f"quality={row.avg_quality_score:.4f} fill={row.avg_fill_rate:.4f} "
                f"reject={row.avg_reject_rate:.4f} sharpe={row.sharpe:.4f} dd={row.max_drawdown:.4f}"
            )
        )

    return write_text_pdf(lines=lines, output_path=output_path)


def generate_monthly_report_artifacts(
    *,
    results_dir: str | Path,
    output_dir: str | Path,
    month: str,
    starting_equity: float = 10_000.0,
) -> MonthlyReportArtifacts:
    """Build monthly report payload and render JSON + HTML + PDF artifacts."""
    report = build_monthly_report(
        results_dir=results_dir,
        month=month,
        starting_equity=float(starting_equity),
    )

    target_dir = Path(output_dir) / report.month
    target_dir.mkdir(parents=True, exist_ok=True)

    base = f"monthly_report_{report.month}"
    json_path = target_dir / f"{base}.json"
    html_path = target_dir / f"{base}.html"
    pdf_path = target_dir / f"{base}.pdf"
    svg_path = target_dir / f"{base}_equity_curve.svg"

    json_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    render_equity_curve_svg(report=report, output_path=svg_path)
    render_monthly_report_html(report=report, output_path=html_path, equity_curve_svg_name=svg_path.name)
    render_monthly_report_pdf(report=report, output_path=pdf_path)

    return MonthlyReportArtifacts(
        report=report,
        json_path=json_path,
        html_path=html_path,
        pdf_path=pdf_path,
        equity_curve_svg_path=svg_path,
    )
