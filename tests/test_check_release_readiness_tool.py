from __future__ import annotations

import json
from pathlib import Path

from tools.check_release_readiness import evaluate_release_readiness


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_release_readiness_passes_with_complete_evidence(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    _write_json(
        registry,
        {
            "schema_version": "1",
            "cohorts": [
                {
                    "release_window": "2026-03",
                    "status": "active",
                    "external_beginner_participants": 2,
                    "external_pro_participants": 2,
                    "internal_proxy_participants": 1,
                    "channels": ["discord"],
                }
            ],
        },
    )

    user_research = tmp_path / "user_research.md"
    user_research.write_text("- `release_window: 2026-03`\n", encoding="utf-8")

    integrations = tmp_path / "integrations.json"
    _write_json(
        integrations,
        [
            {"provider": "binance", "status": "beta", "market_classes": ["crypto"]},
            {"provider": "coinbase", "status": "beta", "market_classes": ["crypto"]},
            {"provider": "alpaca", "status": "beta", "market_classes": ["equities"]},
            {"provider": "oanda", "status": "beta", "market_classes": ["forex"]},
            {"provider": "polymarket", "status": "active", "market_classes": ["prediction_markets"]},
        ],
    )

    certifications = tmp_path / "certifications.json"
    _write_json(
        certifications,
        {
            "all_passed": True,
            "results": [
                {"venue": "binance", "passed": True},
                {"venue": "coinbase", "passed": True},
                {"venue": "alpaca", "passed": True},
                {"venue": "oanda", "passed": True},
            ],
        },
    )

    reference_performance = tmp_path / "reference_performance_latest.json"
    _write_json(
        reference_performance,
        {
            "trust_label": "reference",
            "generated_at": "2026-03-12T05:00:00Z",
            "bundle_count": 3,
            "bundles": [
                {"trust_label": "reference"},
                {"trust_label": "reference"},
                {"trust_label": "reference"},
            ],
        },
    )

    benchmarks_doc = tmp_path / "BENCHMARKS.md"
    benchmarks_doc.write_text("Last updated: 2026-03-12\n", encoding="utf-8")
    issue_backlog = tmp_path / "ISSUE_BACKLOG.md"
    issue_backlog.write_text(
        "Canonical active execution order is maintained in `docs/TODO.md`.\n",
        encoding="utf-8",
    )

    policy = tmp_path / "policy.json"
    _write_json(
        policy,
        {
            "external_beta": {
                "registry": str(registry),
                "user_research": str(user_research),
                "required_statuses": ["active", "completed"],
                "min_external_beginner_participants": 1,
                "min_external_pro_participants": 1,
            },
            "integrations": {
                "index": str(integrations),
                "certification_report": str(certifications),
                "required_venues": ["binance", "coinbase", "alpaca", "oanda"],
                "required_market_classes": ["crypto", "equities", "forex", "prediction_markets"],
                "min_status": "beta",
            },
            "benchmark": {
                "reference_performance": str(reference_performance),
                "min_reference_bundle_count": 3,
                "required_top_level_trust_label": "reference",
                "required_bundle_trust_label": "reference",
            },
            "docs": {
                "benchmarks_doc": str(benchmarks_doc),
                "issue_backlog": str(issue_backlog),
                "require_issue_backlog_archive_marker": "Canonical active execution order is maintained in `docs/TODO.md`.",
            },
        },
    )

    errors, summary = evaluate_release_readiness(policy)
    assert errors == []
    assert summary["passed"] is True
    assert summary["error_count"] == 0


def test_release_readiness_fails_when_external_beta_is_not_ready(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    _write_json(
        registry,
        {
            "schema_version": "1",
            "cohorts": [
                {
                    "release_window": "2026-03",
                    "status": "planned",
                    "external_beginner_participants": 0,
                    "external_pro_participants": 0,
                    "internal_proxy_participants": 2,
                    "channels": ["discord"],
                }
            ],
        },
    )
    user_research = tmp_path / "user_research.md"
    user_research.write_text("- `release_window: 2026-03`\n", encoding="utf-8")

    integrations = tmp_path / "integrations.json"
    _write_json(integrations, [])
    certifications = tmp_path / "certifications.json"
    _write_json(certifications, {"all_passed": False, "results": []})
    reference_performance = tmp_path / "reference_performance_latest.json"
    _write_json(reference_performance, {"bundle_count": 0, "bundles": [], "trust_label": "unverified", "generated_at": ""})
    benchmarks_doc = tmp_path / "BENCHMARKS.md"
    benchmarks_doc.write_text("", encoding="utf-8")
    issue_backlog = tmp_path / "ISSUE_BACKLOG.md"
    issue_backlog.write_text("", encoding="utf-8")

    policy = tmp_path / "policy.json"
    _write_json(
        policy,
        {
            "external_beta": {
                "registry": str(registry),
                "user_research": str(user_research),
                "required_statuses": ["active", "completed"],
                "min_external_beginner_participants": 1,
                "min_external_pro_participants": 1,
            },
            "integrations": {
                "index": str(integrations),
                "certification_report": str(certifications),
                "required_venues": ["binance"],
                "required_market_classes": ["crypto"],
                "min_status": "beta",
            },
            "benchmark": {
                "reference_performance": str(reference_performance),
                "min_reference_bundle_count": 1,
                "required_top_level_trust_label": "reference",
                "required_bundle_trust_label": "reference",
            },
            "docs": {
                "benchmarks_doc": str(benchmarks_doc),
                "issue_backlog": str(issue_backlog),
                "require_issue_backlog_archive_marker": "Canonical active execution order is maintained in `docs/TODO.md`.",
            },
        },
    )

    errors, summary = evaluate_release_readiness(policy)
    assert summary["passed"] is False
    assert any("external_beta: cohort status gate failed" in item for item in errors)
