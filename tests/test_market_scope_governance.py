from __future__ import annotations

from core.market_scope_governance import (
    evaluate_market_scope_request,
    resolve_market_scope_policy,
)


def test_scope_policy_allows_primary_wedge_only() -> None:
    policy = resolve_market_scope_policy({"runtime": {"market_scope_policy": {"primary_wedge_market": "crypto"}}})
    report = evaluate_market_scope_request(
        policy=policy,
        requested_markets=["crypto"],
        readiness={},
    )
    assert report["passed"] is True
    assert report["approved_markets"] == ["crypto"]


def test_scope_policy_blocks_expansion_when_gates_fail() -> None:
    policy = resolve_market_scope_policy(
        {
            "runtime": {
                "market_scope_policy": {
                    "primary_wedge_market": "crypto",
                    "max_additional_markets_per_phase": 1,
                    "readiness_gates": {
                        "min_execution_quality": 0.8,
                        "min_reconciliation_accuracy": 0.99,
                        "max_open_p1_incidents": 0,
                    },
                }
            }
        }
    )
    report = evaluate_market_scope_request(
        policy=policy,
        requested_markets=["crypto", "equities"],
        readiness={"execution_quality": 0.5, "reconciliation_accuracy": 0.95, "open_p1_incidents": 2},
    )
    assert report["passed"] is False
    assert "readiness_gates_failed" in report["reasons"]
