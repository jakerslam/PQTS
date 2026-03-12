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
            {
                "provider": "binance",
                "status": "beta",
                "market_classes": ["crypto"],
                "readiness": {
                    "paper_ok": True,
                    "latency_budget": {"paper_p95_ms": 200, "canary_p95_ms": 160, "live_p95_ms": 120},
                    "reliability_budget": {"min_uptime_pct": 99.0, "max_incidents_30d": 2},
                    "incident_profile": {"recent_incidents": 0, "severity": "low"},
                },
            },
            {
                "provider": "coinbase",
                "status": "beta",
                "market_classes": ["crypto"],
                "readiness": {
                    "paper_ok": True,
                    "latency_budget": {"paper_p95_ms": 200, "canary_p95_ms": 160, "live_p95_ms": 120},
                    "reliability_budget": {"min_uptime_pct": 99.0, "max_incidents_30d": 2},
                    "incident_profile": {"recent_incidents": 0, "severity": "low"},
                },
            },
            {
                "provider": "alpaca",
                "status": "beta",
                "market_classes": ["equities"],
                "readiness": {
                    "paper_ok": True,
                    "latency_budget": {"paper_p95_ms": 220, "canary_p95_ms": 180, "live_p95_ms": 140},
                    "reliability_budget": {"min_uptime_pct": 99.0, "max_incidents_30d": 2},
                    "incident_profile": {"recent_incidents": 0, "severity": "low"},
                },
            },
            {
                "provider": "oanda",
                "status": "beta",
                "market_classes": ["forex"],
                "readiness": {
                    "paper_ok": True,
                    "latency_budget": {"paper_p95_ms": 220, "canary_p95_ms": 180, "live_p95_ms": 140},
                    "reliability_budget": {"min_uptime_pct": 99.0, "max_incidents_30d": 2},
                    "incident_profile": {"recent_incidents": 0, "severity": "low"},
                },
            },
            {
                "provider": "polymarket",
                "status": "active",
                "market_classes": ["prediction_markets"],
                "readiness": {
                    "paper_ok": True,
                    "latency_budget": {"paper_p95_ms": 180, "canary_p95_ms": 140, "live_p95_ms": 120},
                    "reliability_budget": {"min_uptime_pct": 99.5, "max_incidents_30d": 1},
                    "incident_profile": {"recent_incidents": 0, "severity": "low"},
                },
            },
        ],
    )

    integration_requirements = tmp_path / "integration_requirements.json"
    _write_json(
        integration_requirements,
        {
            "defaults": {"required_status_by_stage": {"paper": "beta", "canary": "certified", "live": "certified"}},
            "providers": {
                "binance": {"paper_ok": True},
                "coinbase": {"paper_ok": True},
                "alpaca": {"paper_ok": True},
                "oanda": {"paper_ok": True},
            },
        },
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
                "requirements": str(integration_requirements),
                "certification_report": str(certifications),
                "required_venues": ["binance", "coinbase", "alpaca", "oanda"],
                "required_market_classes": ["crypto", "equities", "forex", "prediction_markets"],
                "min_status": "beta",
                "required_stage": "paper",
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
    _write_json(
        integrations,
        [
            {
                "provider": "binance",
                "status": "experimental",
                "market_classes": ["crypto"],
                "readiness": {
                    "paper_ok": False,
                    "latency_budget": {"paper_p95_ms": 200, "canary_p95_ms": 160, "live_p95_ms": 120},
                    "reliability_budget": {"min_uptime_pct": 99.0, "max_incidents_30d": 2},
                    "incident_profile": {"recent_incidents": 0, "severity": "low"},
                },
            }
        ],
    )
    certifications = tmp_path / "certifications.json"
    _write_json(certifications, {"all_passed": False, "results": []})
    integration_requirements = tmp_path / "integration_requirements.json"
    _write_json(
        integration_requirements,
        {
            "defaults": {"required_status_by_stage": {"paper": "beta"}},
            "providers": {"binance": {"paper_ok": True}},
        },
    )
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
                "requirements": str(integration_requirements),
                "certification_report": str(certifications),
                "required_venues": ["binance"],
                "required_market_classes": ["crypto"],
                "min_status": "beta",
                "required_stage": "paper",
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


def test_release_readiness_reports_missing_certification_file_without_crash(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    _write_json(
        registry,
        {
            "schema_version": "1",
            "cohorts": [
                {
                    "release_window": "2026-03",
                    "status": "active",
                    "external_beginner_participants": 1,
                    "external_pro_participants": 1,
                    "internal_proxy_participants": 0,
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
            {
                "provider": "binance",
                "status": "beta",
                "market_classes": ["crypto", "prediction_markets", "equities", "forex"],
                "readiness": {
                    "paper_ok": True,
                    "latency_budget": {"paper_p95_ms": 200, "canary_p95_ms": 150, "live_p95_ms": 120},
                    "reliability_budget": {"min_uptime_pct": 99.0, "max_incidents_30d": 1},
                    "incident_profile": {"recent_incidents": 0, "severity": "low"},
                },
            }
        ],
    )
    reference_performance = tmp_path / "reference_performance_latest.json"
    _write_json(
        reference_performance,
        {
            "trust_label": "reference",
            "generated_at": "2026-03-12T00:00:00Z",
            "bundle_count": 1,
            "bundles": [{"trust_label": "reference"}],
        },
    )
    benchmarks_doc = tmp_path / "BENCHMARKS.md"
    benchmarks_doc.write_text("2026-03-12\n", encoding="utf-8")
    issue_backlog = tmp_path / "ISSUE_BACKLOG.md"
    issue_backlog.write_text("Canonical active execution order is maintained in `docs/TODO.md`.\n", encoding="utf-8")
    requirements = tmp_path / "requirements.json"
    _write_json(requirements, {"providers": {"binance": {"paper_ok": True}}})

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
                "requirements": str(requirements),
                "certification_report": str(tmp_path / "missing.json"),
                "required_venues": ["binance"],
                "required_market_classes": ["crypto"],
                "min_status": "beta",
                "required_stage": "paper",
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
    assert any("integrations: certification report missing:" in item for item in errors)
