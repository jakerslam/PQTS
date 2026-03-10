from __future__ import annotations

import json
from pathlib import Path

from analytics.monthly_report_pipeline import (
    build_monthly_report,
    discover_month_bundles,
    generate_monthly_report_artifacts,
)


def _write_bundle(
    root: Path,
    bundle_name: str,
    payload: dict,
) -> Path:
    bundle = root / bundle_name
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "simulation_suite_20260309T000000000000Z.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    return bundle


def test_discover_month_bundles_filters_prefix(tmp_path: Path) -> None:
    results = tmp_path / "results"
    results.mkdir()
    (results / "2026-03-09_bundle_a").mkdir()
    (results / "2026-03-11_bundle_b").mkdir()
    (results / "2026-02-28_bundle_old").mkdir()
    (results / "misc").mkdir()

    bundles = discover_month_bundles(results, "2026-03")
    assert [path.name for path in bundles] == ["2026-03-09_bundle_a", "2026-03-11_bundle_b"]


def test_build_monthly_report_aggregates_metrics(tmp_path: Path) -> None:
    results = tmp_path / "results"
    results.mkdir()

    payload = {
        "created_at": "2026-03-09T18:07:50.585697+00:00",
        "leaderboard": [
            {
                "market": "crypto",
                "strategy": "market_making",
                "runs": 2,
                "avg_quality_score": 0.35,
                "avg_fill_rate": 0.60,
                "avg_reject_rate": 0.40,
            }
        ],
        "results": [
            {
                "quality_score": 0.30,
                "filled": 6,
                "submitted": 10,
                "reject_rate": 0.40,
                "scenario": {"market": "crypto", "strategy": "market_making", "notional_usd": 100.0},
            },
            {
                "quality_score": -0.10,
                "filled": 4,
                "submitted": 10,
                "reject_rate": 0.60,
                "scenario": {"market": "crypto", "strategy": "market_making", "notional_usd": 100.0},
            },
        ],
    }
    _write_bundle(results, "2026-03-09_bundle_a", payload)

    report = build_monthly_report(results_dir=results, month="2026-03", starting_equity=10_000.0)

    assert report.bundle_count == 1
    assert report.scenario_count == 2
    assert report.total_pnl == 20.0
    assert report.ending_equity == 10_020.0
    assert report.max_drawdown >= 0.0
    assert len(report.attribution_rows) == 1
    row = report.attribution_rows[0]
    assert row.market == "crypto"
    assert row.strategy == "market_making"
    assert row.runs == 2
    assert row.total_pnl == 20.0


def test_generate_monthly_report_artifacts_writes_json_html_pdf(tmp_path: Path) -> None:
    results = tmp_path / "results"
    output = tmp_path / "out"
    results.mkdir()

    payload = {
        "created_at": "2026-03-10T02:00:00+00:00",
        "leaderboard": [
            {
                "market": "equities",
                "strategy": "funding_arbitrage",
                "runs": 1,
                "avg_quality_score": 0.20,
                "avg_fill_rate": 0.50,
                "avg_reject_rate": 0.50,
            }
        ],
        "results": [
            {
                "quality_score": 0.20,
                "filled": 5,
                "submitted": 10,
                "reject_rate": 0.50,
                "scenario": {
                    "market": "equities",
                    "strategy": "funding_arbitrage",
                    "notional_usd": 80.0,
                },
            }
        ],
    }
    _write_bundle(results, "2026-03-10_bundle_b", payload)

    artifacts = generate_monthly_report_artifacts(
        results_dir=results,
        output_dir=output,
        month="2026-03",
        starting_equity=5_000.0,
    )

    assert artifacts.json_path.exists()
    assert artifacts.html_path.exists()
    assert artifacts.pdf_path.exists()
    assert artifacts.equity_curve_svg_path.exists()

    rendered = artifacts.html_path.read_text(encoding="utf-8")
    assert "PQTS Monthly Benchmark Report - 2026-03" in rendered
    assert "Attribution Table" in rendered

    payload = json.loads(artifacts.json_path.read_text(encoding="utf-8"))
    assert payload["month"] == "2026-03"
    assert payload["bundle_count"] == 1
    assert payload["scenario_count"] == 1
