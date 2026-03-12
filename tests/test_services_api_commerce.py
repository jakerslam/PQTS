"""Tests for billing and monetization helper utilities."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.api.commerce import (  # noqa: E402
    build_workspace_subscription,
    create_checkout_session,
    load_plan_catalog,
    marketplace_commission,
    resolve_plan,
)
from services.api.config import APISettings  # noqa: E402


def test_plan_catalog_and_alias_resolution() -> None:
    settings = APISettings(plan_catalog_path="config/monetization/plan_catalog.json")
    catalog = load_plan_catalog(settings)
    assert resolve_plan(catalog, "starter") == "starter_cloud"
    assert resolve_plan(catalog, "pro") == "pro_cloud"
    assert resolve_plan(catalog, "enterprise") == "enterprise"
    assert resolve_plan(catalog, "") == str(catalog.get("default_plan"))


def test_build_workspace_subscription_sets_trial_window_for_paid_plans() -> None:
    settings = APISettings(plan_catalog_path="config/monetization/plan_catalog.json")
    catalog = load_plan_catalog(settings)
    sub = build_workspace_subscription(
        workspace_id="ws_abc",
        plan="pro_cloud",
        actor="tester",
        catalog=catalog,
        status="trialing",
        trial_days=14,
    )
    assert sub["workspace_id"] == "ws_abc"
    assert sub["plan"] == "pro_cloud"
    assert sub["status"] == "trialing"
    assert sub["trial_ends_at"] != ""


def test_create_checkout_session_uses_dry_run_when_provider_is_demo() -> None:
    settings = APISettings(
        billing_provider="demo",
        plan_catalog_path="config/monetization/plan_catalog.json",
    )
    catalog = load_plan_catalog(settings)
    session = create_checkout_session(
        settings=settings,
        catalog=catalog,
        workspace_id="ws_abc",
        plan="pro_cloud",
        customer_email="user@example.com",
        success_url="https://app.example/success",
        cancel_url="https://app.example/cancel",
        dry_run=True,
    )
    assert session["dry_run"] is True
    assert session["live"] is False
    assert session["checkout_url"].startswith("https://billing.pqts.local/checkout/")


def test_marketplace_commission_calculation() -> None:
    settings = APISettings(plan_catalog_path="config/monetization/plan_catalog.json")
    catalog = load_plan_catalog(settings)
    payout = marketplace_commission(catalog, 120.0)
    assert payout["gross_amount_usd"] == 120.0
    assert payout["commission_amount_usd"] == 30.0
    assert payout["seller_net_amount_usd"] == 90.0
