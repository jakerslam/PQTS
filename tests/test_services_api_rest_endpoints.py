"""Tests for core API REST resources."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from services.api.app import create_app
from services.api.config import APISettings


def _settings() -> APISettings:
    return APISettings(
        service_name="PQTS API Test",
        service_version="9.9.9",
        environment="test",
        auth_tokens="admin-token:admin,operator-token:operator,viewer-token:viewer",
    )


def _viewer() -> dict[str, str]:
    return {"Authorization": "Bearer viewer-token"}


def _operator() -> dict[str, str]:
    return {"Authorization": "Bearer operator-token"}


def test_get_account_summary_for_default_bootstrap_account() -> None:
    client = TestClient(create_app(_settings()))
    response = client.get("/v1/accounts/paper-main", headers=_viewer())
    assert response.status_code == 200
    payload = response.json()["account"]
    assert payload["account_id"] == "paper-main"
    assert payload["currency"] == "USD"


def test_post_order_requires_operator_role() -> None:
    client = TestClient(create_app(_settings()))
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "order_id": "ord-1",
        "account_id": "paper-main",
        "symbol": "BTC-USD",
        "side": "buy",
        "order_type": "limit",
        "status": "open",
        "quantity": 1.0,
        "filled_quantity": 0.0,
        "remaining_quantity": 1.0,
        "submitted_at": now,
        "updated_at": now,
        "limit_price": 40_000.0,
        "stop_price": None,
        "time_in_force": "gtc",
    }

    denied = client.post("/v1/execution/orders", json=payload, headers=_viewer())
    assert denied.status_code == 403

    allowed = client.post("/v1/execution/orders", json=payload, headers=_operator())
    assert allowed.status_code == 200

    listed = client.get("/v1/execution/orders", params={"account_id": "paper-main"}, headers=_viewer())
    assert listed.status_code == 200
    orders = listed.json()["orders"]
    assert any(item["order_id"] == "ord-1" for item in orders)


def test_risk_state_upsert_and_fetch() -> None:
    client = TestClient(create_app(_settings()))
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "risk_level": "elevated",
        "max_drawdown": 0.15,
        "current_drawdown": 0.07,
        "var_95": 0.03,
        "exposure": 0.42,
        "kill_switch_active": False,
        "reasons": ["volatility_spike"],
        "as_of": now,
    }

    write = client.put("/v1/risk/state/paper-main", json=payload, headers=_operator())
    assert write.status_code == 200
    assert write.json()["risk_state"]["risk_level"] == "elevated"

    read = client.get("/v1/risk/state/paper-main", headers=_viewer())
    assert read.status_code == 200
    assert read.json()["risk_state"]["current_drawdown"] == 0.07


def test_operator_actions_append_and_list() -> None:
    client = TestClient(create_app(_settings()))

    write = client.post(
        "/v1/operator/actions",
        json={"kind": "pause_trading", "actor": "ops", "note": "incident triage"},
        headers=_operator(),
    )
    assert write.status_code == 200
    action = write.json()["action"]
    assert action["kind"] == "pause_trading"

    listed = client.get("/v1/operator/actions", headers=_viewer())
    assert listed.status_code == 200
    actions = listed.json()["actions"]
    assert any(row["kind"] == "pause_trading" for row in actions)


def test_promotions_action_flow() -> None:
    client = TestClient(create_app(_settings()))

    baseline = client.get("/v1/promotions", headers=_viewer())
    assert baseline.status_code == 200
    records = baseline.json()["records"]
    assert any(row["strategy_id"] == "trend_following" for row in records)

    write = client.post(
        "/v1/promotions/actions",
        json={"strategy_id": "trend_following", "action": "advance", "actor": "ops"},
        headers=_operator(),
    )
    assert write.status_code == 200
    updated = write.json()["updated"]
    assert updated["strategy_id"] == "trend_following"
    assert updated["stage"] in {"shadow", "canary", "live", "paper", "backtest", "halted"}
    assert len(updated["history"]) >= 1


def test_ops_diagnostics_surfaces_return_payload_shapes() -> None:
    client = TestClient(create_app(_settings()))

    execution = client.get("/v1/ops/execution-quality", headers=_viewer())
    assert execution.status_code == 200
    assert "summary" in execution.json()
    assert "chart_points" in execution.json()
    assert "rows" in execution.json()

    truth = client.get("/v1/ops/order-truth", headers=_viewer())
    assert truth.status_code == 200
    assert "rows" in truth.json()
    assert "explanation" in truth.json()
    assert "evidence_bundle" in truth.json()

    replay = client.get("/v1/ops/replay", headers=_viewer())
    assert replay.status_code == 200
    assert "event_types" in replay.json()
    assert "events" in replay.json()

    gallery = client.get("/v1/ops/template-gallery", headers=_viewer())
    assert gallery.status_code == 200
    assert "artifacts" in gallery.json()

    reference = client.get("/v1/ops/reference-performance", headers=_viewer())
    assert reference.status_code == 200
    assert "bundle_count" in reference.json()
    assert "provenance" in reference.json()


def test_ops_command_endpoints_support_dry_run() -> None:
    client = TestClient(create_app(_settings()))

    presets = client.get("/v1/ops/data-seed/presets", headers=_viewer())
    assert presets.status_code == 200
    assert "presets" in presets.json()

    data_seed = client.post("/v1/ops/data-seed/run", json={"execute": False}, headers=_operator())
    assert data_seed.status_code == 200
    data_payload = data_seed.json()
    assert data_payload["dry_run"] is True
    assert "python" in data_payload["command"][0]

    notify = client.post("/v1/ops/notify/test", json={"execute": False}, headers=_operator())
    assert notify.status_code == 200
    notify_payload = notify.json()
    assert notify_payload["dry_run"] is True
    assert "python" in notify_payload["command"][0]


def test_ops_command_endpoints_execute_via_job_contract() -> None:
    mocked_result = {
        "succeeded": True,
        "returncode": 0,
        "stdout": '{"status":"ok","channel":"stdout"}\n',
        "stderr": "",
        "duration_ms": 8,
        "command": ["python3", "main.py", "notify", "test"],
    }
    with patch("services.api.routes.core.run_python_command", return_value=mocked_result):
        client = TestClient(create_app(_settings()))
        started = client.post(
            "/v1/ops/notify/test",
            json={"execute": True, "channel": "stdout", "message": "job flow"},
            headers=_operator(),
        )
        assert started.status_code == 200
        payload = started.json()
        assert payload["accepted"] is True
        assert payload["dry_run"] is False
        job_id = payload["job"]["job_id"]
        assert job_id.startswith("job_")

        deadline = time.time() + 2.0
        final_status = ""
        while time.time() < deadline:
            polled = client.get(f"/v1/ops/jobs/{job_id}", headers=_viewer())
            assert polled.status_code == 200
            job = polled.json()["job"]
            final_status = str(job.get("status", ""))
            if final_status in {"succeeded", "failed"}:
                break
            time.sleep(0.05)
        assert final_status == "succeeded"

        listed = client.get("/v1/ops/jobs", headers=_viewer())
        assert listed.status_code == 200
        assert listed.json()["count"] >= 1
        assert any(row["job_id"] == job_id for row in listed.json()["jobs"])


def test_assistant_turn_returns_constrained_suggestions() -> None:
    client = TestClient(create_app(_settings()))
    response = client.post("/v1/assistant/turn", json={"message": "show risk and reject reasons"}, headers=_viewer())
    assert response.status_code == 200
    payload = response.json()
    assert "assistant_message" in payload
    assert isinstance(payload.get("suggestions"), list)
    assert any("/dashboard/risk" in str(item.get("href", "")) for item in payload.get("suggestions", []))


def test_onboarding_run_start_and_status_progression() -> None:
    client = TestClient(create_app(_settings()))
    started = client.post(
        "/v1/onboarding/runs",
        json={"experience": "beginner", "automation": "manual", "capital_usd": 5000},
        headers=_viewer(),
    )
    assert started.status_code == 200
    payload = started.json()
    assert "run" in payload
    assert "plan" in payload
    run_id = payload["run"]["run_id"]
    assert run_id.startswith("run_")

    deadline = time.time() + 6.0
    latest_status = payload["run"]["status"]
    while time.time() < deadline:
        polled = client.get(f"/v1/onboarding/runs/{run_id}", headers=_viewer())
        assert polled.status_code == 200
        latest = polled.json()["run"]
        latest_status = latest["status"]
        if latest_status == "completed":
            assert isinstance(latest.get("steps"), list)
            assert len(latest.get("artifacts", [])) >= 1
            assert latest.get("meets_under_5_minute_goal") is True
            break
        time.sleep(0.2)
    assert latest_status == "completed"


def test_plaid_link_flow_defaults_to_read_only_and_aggregates_accounts() -> None:
    client = TestClient(create_app(_settings()))

    start = client.post(
        "/v1/integrations/brokerage/plaid/link/start",
        json={"institution": "alpaca", "scope": "trade_enabled"},
        headers=_viewer(),
    )
    assert start.status_code == 200
    start_payload = start.json()
    assert start_payload["provider"] == "plaid"
    assert start_payload["scope"] == "read_only"
    assert start_payload["trade_permission_enabled"] is False
    link_id = start_payload["link_id"]

    complete = client.post(
        "/v1/integrations/brokerage/plaid/link/complete",
        json={"link_id": link_id, "public_token": "public-sandbox-token"},
        headers=_viewer(),
    )
    assert complete.status_code == 200
    completed = complete.json()
    assert completed["connection"]["status"] == "connected"
    assert completed["connection"]["trade_permission_enabled"] is False
    assert len(completed["accounts"]) >= 1

    listed = client.get("/v1/integrations/brokerage/accounts", headers=_viewer())
    assert listed.status_code == 200
    accounts = listed.json()["accounts"]
    assert len(accounts) >= 1
    assert listed.json()["totals"]["total_balance_current_usd"] > 0


def test_brokerage_sync_health_fail_closed_and_manual_sync_receipt() -> None:
    client = TestClient(create_app(_settings()))

    start = client.post(
        "/v1/integrations/brokerage/plaid/link/start",
        json={"institution": "coinbase"},
        headers=_viewer(),
    )
    link_id = start.json()["link_id"]
    complete = client.post(
        "/v1/integrations/brokerage/plaid/link/complete",
        json={"link_id": link_id, "public_token": "token-1"},
        headers=_viewer(),
    )
    assert complete.status_code == 200

    stale_state = client.get("/v1/integrations/brokerage/sync-health", headers=_viewer())
    assert stale_state.status_code == 200
    rows = stale_state.json()["connections"]
    assert any(row["link_id"] == link_id for row in rows)

    sync = client.post("/v1/integrations/brokerage/sync", json={"link_id": link_id}, headers=_operator())
    assert sync.status_code == 200
    assert link_id in sync.json()["synced_links"]
    assert "synced_at" in sync.json()

    refreshed = client.get("/v1/integrations/brokerage/sync-health", headers=_viewer())
    assert refreshed.status_code == 200
    updated = [row for row in refreshed.json()["connections"] if row["link_id"] == link_id][0]
    assert updated["status"] in {"ok", "stale"}
    assert updated["stale_after_seconds"] >= 1


def test_terminal_and_assistant_audit_surface_are_persisted() -> None:
    client = TestClient(create_app(_settings()))

    prefs = client.put(
        "/v1/studio/terminal/preferences",
        json={"density": "pro", "watchlist": ["BTC-USD", "SOL-USD"], "refresh_seconds": 3},
        headers=_viewer(),
    )
    assert prefs.status_code == 200
    assert prefs.json()["profile"]["density"] == "pro"

    terminal = client.get("/v1/studio/terminal", headers=_viewer())
    assert terminal.status_code == 200
    terminal_payload = terminal.json()
    assert terminal_payload["always_on"] is True
    assert terminal_payload["profile"]["density"] == "pro"
    assert "portfolio_totals" in terminal_payload

    assistant = client.post(
        "/v1/assistant/turn",
        json={"message": "please rebalance positions", "requested_action": "rebalance"},
        headers=_viewer(),
    )
    assert assistant.status_code == 200
    payload = assistant.json()
    assert payload["action_policy"]["capital_affecting"] is True
    assert payload["action_policy"]["executed"] is False
    assert payload["action_policy"]["mode"] == "requires_confirmation"
    assert payload["audit_id"].startswith("ast_")

    audit = client.get("/v1/assistant/audit", headers=_viewer())
    assert audit.status_code == 200
    events = audit.json()["events"]
    assert len(events) >= 1
    assert events[0]["id"].startswith("ast_")


def test_agent_context_intent_simulate_execute_and_receipts() -> None:
    client = TestClient(create_app(_settings()))

    me = client.get("/v1/auth/me", headers=_viewer())
    assert me.status_code == 200
    agent_id = me.json()["identity"]["subject"]

    policy_write = client.put(
        f"/v1/agent/policies/{agent_id}",
        json={
            "capabilities": {
                "read": True,
                "propose": True,
                "simulate": True,
                "execute": True,
                "hooks_manage": True,
            }
        },
        headers=_operator(),
    )
    assert policy_write.status_code == 200
    assert policy_write.json()["policy"]["capabilities"]["execute"] is True

    context = client.get("/v1/agent/context", headers=_viewer())
    assert context.status_code == 200
    context_payload = context.json()
    assert context_payload["agent_id"] == agent_id
    assert "system_facts" in context_payload
    assert "current_state" in context_payload

    create_intent = client.post(
        "/v1/agent/intents",
        json={
            "action": "demote",
            "strategy_id": "trend_following",
            "rationale": "Reduce exposure while preserving paper-first controls.",
            "supporting_card_ids": ["card-001"],
            "current_metrics": {"reject_rate": 0.01, "fill_rate": 0.99},
            "gate_checks": {"readiness": True},
            "risk_impact": {"expected_drawdown_delta": -0.01},
        },
        headers=_viewer(),
    )
    assert create_intent.status_code == 200
    intent = create_intent.json()["intent"]
    intent_id = intent["intent_id"]
    assert intent["status"] == "proposed"

    sim = client.post(f"/v1/agent/intents/{intent_id}/simulate", headers=_viewer())
    assert sim.status_code == 200
    sim_payload = sim.json()
    assert sim_payload["simulation"]["passed"] is True
    sim_receipt_id = sim_payload["receipt"]["receipt_id"]

    receipt = client.get(f"/v1/agent/receipts/{sim_receipt_id}", headers=_viewer())
    assert receipt.status_code == 200
    assert receipt.json()["receipt"]["type"] == "intent_simulated"

    execute = client.post(f"/v1/agent/intents/{intent_id}/execute", headers=_operator())
    assert execute.status_code == 200
    execute_payload = execute.json()
    assert execute_payload["intent"]["status"] == "executed"
    assert execute_payload["promotion"]["strategy_id"] == "trend_following"
    assert execute_payload["receipt"]["type"] == "intent_executed"


def test_agent_hooks_allowlist_and_delete_flow() -> None:
    client = TestClient(create_app(_settings()))

    bad = client.post(
        "/v1/agent/hooks",
        json={"event_type": "intent_status", "target_url": "https://evil.example.com/hook"},
        headers=_viewer(),
    )
    assert bad.status_code == 400

    created = client.post(
        "/v1/agent/hooks",
        json={
            "event_type": "intent_status",
            "target_url": "https://hooks.slack.com/services/T000/B000/XYZ",
            "secret": "top-secret-token",
        },
        headers=_viewer(),
    )
    assert created.status_code == 200
    hook = created.json()["hook"]
    hook_id = hook["hook_id"]
    assert hook["status"] == "active"
    assert hook["secret_fingerprint"] != ""

    listed = client.get("/v1/agent/hooks", headers=_viewer())
    assert listed.status_code == 200
    assert listed.json()["count"] >= 1
    assert any(row["hook_id"] == hook_id for row in listed.json()["hooks"])

    deleted = client.delete(f"/v1/agent/hooks/{hook_id}", headers=_viewer())
    assert deleted.status_code == 200
    assert deleted.json()["hook"]["status"] == "deleted"


def test_agent_execute_requires_operator_role_even_with_policy() -> None:
    client = TestClient(create_app(_settings()))
    me = client.get("/v1/auth/me", headers=_viewer())
    assert me.status_code == 200
    agent_id = me.json()["identity"]["subject"]
    client.put(
        f"/v1/agent/policies/{agent_id}",
        json={"capabilities": {"read": True, "propose": True, "simulate": True, "execute": True, "hooks_manage": True}},
        headers=_operator(),
    )

    create_intent = client.post(
        "/v1/agent/intents",
        json={
            "action": "hold",
            "strategy_id": "market_making",
            "rationale": "No-op validation action.",
            "supporting_card_ids": ["card-002"],
            "current_metrics": {"reject_rate": 0.0},
            "gate_checks": {"ready": True},
            "risk_impact": {"expected_drawdown_delta": 0.0},
        },
        headers=_viewer(),
    )
    assert create_intent.status_code == 200
    intent_id = create_intent.json()["intent"]["intent_id"]
    sim = client.post(f"/v1/agent/intents/{intent_id}/simulate", headers=_viewer())
    assert sim.status_code == 200

    denied = client.post(f"/v1/agent/intents/{intent_id}/execute", headers=_viewer())
    assert denied.status_code == 403


def test_agent_default_policy_blocks_execute_even_for_operator() -> None:
    client = TestClient(create_app(_settings()))
    created = client.post(
        "/v1/agent/intents",
        json={
            "action": "promote_to_paper",
            "strategy_id": "trend_following",
            "rationale": "default policy should still deny execute",
            "supporting_card_ids": ["card-1"],
            "current_metrics": {"fill_rate": 0.9},
            "gate_checks": {"paper_days": 30},
            "risk_impact": {"delta_var_pct": 0.2},
        },
        headers=_viewer(),
    )
    assert created.status_code == 200
    intent_id = created.json()["intent"]["intent_id"]

    simulated = client.post(f"/v1/agent/intents/{intent_id}/simulate", headers=_viewer())
    assert simulated.status_code == 200
    assert simulated.json()["simulation"]["passed"] is True

    denied = client.post(f"/v1/agent/intents/{intent_id}/execute", headers=_operator())
    assert denied.status_code == 403


def test_strategy_studio_preview_training_and_gate_evaluation_contracts() -> None:
    client = TestClient(create_app(_settings()))

    preview = client.post(
        "/v1/studio/strategy/preview",
        json={
            "strategy_id": "trend_following",
            "code": "def signal(x):\n    return x\n",
            "nodes": [{"node_id": "n1", "kind": "signal", "params": {"window": 20}}],
            "edges": [["n1", "sink"]],
            "sample_rows": [{"feature_ts": "2026-03-10T00:00:00", "target_ts": "2026-03-10T00:00:00"}],
        },
        headers=_viewer(),
    )
    assert preview.status_code == 200
    preview_payload = preview.json()
    assert preview_payload["compile_report"]["compiled"] is True
    assert preview_payload["leakage_report"]["passed"] is True
    assert "PASS no-lookahead validation" in preview_payload["leakage_summary"]

    train = client.post(
        "/v1/studio/strategy/train",
        json={
            "strategy_id": "trend_following",
            "mode": "adaptive",
            "candidate_models": [{"score": 0.61}, {"score": 0.64}],
            "retrain_on_live_data": True,
            "optuna_trials": 32,
        },
        headers=_operator(),
    )
    assert train.status_code == 200
    assert train.json()["artifact"]["mode"] == "adaptive_ensemble"

    gates = client.post(
        "/v1/promotions/gate-evaluate",
        json={
            "strategy_id": "trend_following",
            "metrics": {
                "net_expectancy": 0.12,
                "calibration_stability": 0.91,
                "max_drawdown_observed": 0.09,
                "realized_net_alpha": 42.0,
                "sample_size": 400,
                "critical_violations": 0,
                "slippage_mape": 0.08,
                "paper_campaign_passed": True,
                "unresolved_high_severity_incidents": 0,
                "stress_replay_passed": True,
                "portfolio_limits_intact": True,
            },
        },
        headers=_operator(),
    )
    assert gates.status_code == 200
    assert gates.json()["passed"] is True
    assert gates.json()["decision"] == "advance"


def test_failover_instrument_and_marketplace_endpoints() -> None:
    client = TestClient(create_app(_settings()))

    failover = client.post(
        "/v1/execution/failover/evaluate",
        json={
            "venues": [
                {"venue": "binance", "latency_ms": 25, "reject_rate": 0.01, "connected": True, "liquidity_score": 0.95},
                {"venue": "coinbase", "latency_ms": 45, "reject_rate": 0.02, "connected": True, "liquidity_score": 0.9},
            ]
        },
        headers=_viewer(),
    )
    assert failover.status_code == 200
    assert failover.json()["primary"]["venue"] == "binance"
    assert failover.json()["fallback"]["venue"] == "coinbase"

    normalized = client.get(
        "/v1/instruments/normalize",
        params={"venue": "oanda", "symbol": "EUR/USD", "market": "forex"},
        headers=_viewer(),
    )
    assert normalized.status_code == 200
    assert normalized.json()["instrument"]["asset_class"] == "forex"

    listing = client.post(
        "/v1/marketplace/listings",
        json={
            "strategy_id": "trend_following",
            "title": "Trend Following Reference",
            "version": "0.2.0",
            "author": "ops",
            "verified_badge": True,
            "reputation_score": 0.83,
            "promotion_stage": "canary",
            "trust_label": "reference",
        },
        headers=_operator(),
    )
    assert listing.status_code == 200
    assert listing.json()["listing"]["strategy_id"] == "trend_following"

    listings = client.get("/v1/marketplace/listings", headers=_viewer())
    assert listings.status_code == 200
    assert listings.json()["count"] >= 1
    assert listings.json()["verified_count"] >= 1


def test_signup_requires_disclaimer_and_paper_first_acceptance() -> None:
    client = TestClient(create_app(_settings()))
    denied = client.post(
        "/v1/signup",
        json={
            "email": "ops@example.com",
            "organization": "Ops Team",
            "plan": "starter",
            "accepted_risk_disclaimer": False,
            "accepted_paper_first_policy": False,
        },
        headers=_viewer(),
    )
    assert denied.status_code == 400


def test_workspace_signup_subscribe_campaign_and_health_contracts() -> None:
    client = TestClient(create_app(_settings()))

    signup = client.post(
        "/v1/signup",
        json={
            "email": "ops@example.com",
            "organization": "Ops Team",
            "plan": "starter",
            "accepted_risk_disclaimer": True,
            "accepted_paper_first_policy": True,
        },
        headers=_viewer(),
    )
    assert signup.status_code == 200
    workspace = signup.json()["workspace"]
    workspace_id = workspace["workspace_id"]
    assert workspace["plan"] == "starter_cloud"

    subscribe = client.post(
        f"/v1/workspaces/{workspace_id}/billing/subscribe",
        json={
            "plan": "pro",
            "create_checkout_session": True,
            "dry_run": True,
            "success_url": "https://app.example/success",
            "cancel_url": "https://app.example/cancel",
        },
        headers=_viewer(),
    )
    assert subscribe.status_code == 200
    sub_payload = subscribe.json()
    assert sub_payload["workspace"]["plan"] == "pro_cloud"
    assert sub_payload["checkout"]["dry_run"] is True

    campaign = client.post(
        f"/v1/workspaces/{workspace_id}/campaign/start",
        json={"execute": False, "cycles": 4, "notional_usd": 100.0},
        headers=_viewer(),
    )
    assert campaign.status_code == 200
    assert campaign.json()["dry_run"] is True
    assert "python" in campaign.json()["command"][0]

    health = client.get(f"/v1/workspaces/{workspace_id}/ops-health", headers=_viewer())
    assert health.status_code == 200
    assert "ops_health" in health.json()
    assert "subscription" in health.json()

    gate = client.get(
        f"/v1/workspaces/{workspace_id}/promotion-gate",
        params={"strategy_id": "trend_following"},
        headers=_viewer(),
    )
    assert gate.status_code == 200
    assert "promotion_gate" in gate.json()
    assert "gate" in gate.json()["promotion_gate"]


def test_marketplace_sale_and_revenue_summary_contracts() -> None:
    client = TestClient(create_app(_settings()))

    signup = client.post(
        "/v1/signup",
        json={
            "email": "buyer@example.com",
            "organization": "Buyer Workspace",
            "plan": "community",
            "accepted_risk_disclaimer": True,
            "accepted_paper_first_policy": True,
        },
        headers=_viewer(),
    )
    assert signup.status_code == 200
    workspace_id = signup.json()["workspace"]["workspace_id"]

    sale = client.post(
        "/v1/marketplace/sales/record",
        json={
            "listing_id": "listing_market_making_reference",
            "buyer_workspace_id": workspace_id,
            "gross_amount_usd": 200.0,
            "seller_id": "author_1",
        },
        headers=_operator(),
    )
    assert sale.status_code == 200
    sale_payload = sale.json()["sale"]
    assert sale_payload["commission_amount_usd"] == 50.0
    assert sale_payload["seller_net_amount_usd"] == 150.0

    summary = client.get("/v1/marketplace/revenue-summary", headers=_operator())
    assert summary.status_code == 200
    assert summary.json()["count"] >= 1
    assert summary.json()["commission_amount_usd"] >= 50.0
