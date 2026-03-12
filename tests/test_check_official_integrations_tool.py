from __future__ import annotations

from datetime import date

from tools.check_official_integrations import evaluate_integrations


def _valid_row(provider: str, *, status: str = "beta") -> dict[str, object]:
    return {
        "id": f"{provider}-sdk",
        "provider": provider,
        "repo_url": f"https://github.com/example/{provider}",
        "surface": "sdk",
        "owner": "integration-team",
        "status": status,
        "last_reviewed": "2026-03-12",
        "readiness": {
            "paper_ok": True,
            "latency_budget": {
                "paper_p95_ms": 200,
                "canary_p95_ms": 150,
                "live_p95_ms": 120,
            },
            "reliability_budget": {
                "min_uptime_pct": 99.0,
                "max_incidents_30d": 2,
            },
            "incident_profile": {"recent_incidents": 0, "severity": "low"},
        },
    }


def test_integrations_validator_passes_with_requirements_contract() -> None:
    rows = [
        _valid_row("binance"),
        _valid_row("coinbase"),
    ]
    requirements = {
        "providers": {
            "binance": {"paper_ok": True},
            "coinbase": {"paper_ok": True},
        }
    }
    errors = evaluate_integrations(
        rows,
        requirements=requirements,
        max_age_days=365,
        today=date(2026, 3, 12),
    )
    assert errors == []


def test_integrations_validator_flags_missing_readiness_fields() -> None:
    row = _valid_row("binance")
    row["readiness"] = {"paper_ok": True}
    errors = evaluate_integrations(
        [row],
        requirements={"providers": {"binance": {}}},
        max_age_days=365,
        today=date(2026, 3, 12),
    )
    assert any("readiness.latency_budget must be object" in item for item in errors)
    assert any("readiness.reliability_budget must be object" in item for item in errors)
    assert any("readiness.incident_profile must be object" in item for item in errors)


def test_integrations_validator_flags_requirement_provider_drift() -> None:
    rows = [_valid_row("binance")]
    requirements = {
        "providers": {
            "binance": {},
            "coinbase": {},
        }
    }
    errors = evaluate_integrations(
        rows,
        requirements=requirements,
        max_age_days=365,
        today=date(2026, 3, 12),
    )
    assert any("missing providers declared in requirements" in item for item in errors)
