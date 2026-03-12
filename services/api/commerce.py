"""Billing, plan-catalog, and marketplace commission helpers."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

from services.api.config import APISettings


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_plan_catalog() -> dict[str, Any]:
    return {
        "default_plan": "community",
        "aliases": {"starter": "starter_cloud", "pro": "pro_cloud", "enterprise": "enterprise"},
        "marketplace": {"commission_rate": 0.25},
        "plans": {
            "community": {"display_name": "Community", "price_monthly_usd": 0},
            "starter_cloud": {"display_name": "Starter Cloud", "price_monthly_usd": 49},
            "pro_cloud": {"display_name": "Pro Cloud", "price_monthly_usd": 299},
            "enterprise": {"display_name": "Enterprise", "price_monthly_usd": 999},
        },
    }


def load_plan_catalog(settings: APISettings) -> dict[str, Any]:
    path = Path(settings.plan_catalog_path).expanduser()
    if not path.exists():
        return _default_plan_catalog()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return _default_plan_catalog()
    if not isinstance(payload, dict):
        return _default_plan_catalog()
    plans = payload.get("plans", {})
    if not isinstance(plans, dict) or not plans:
        return _default_plan_catalog()
    return payload


def resolve_plan(catalog: dict[str, Any], requested_plan: str | None) -> str:
    plans = catalog.get("plans", {})
    if not isinstance(plans, dict):
        plans = {}
    aliases = catalog.get("aliases", {})
    if not isinstance(aliases, dict):
        aliases = {}
    default_plan = str(catalog.get("default_plan", "community")).strip().lower() or "community"
    token = str(requested_plan or "").strip().lower()
    if not token:
        return default_plan if default_plan in plans else "community"
    resolved = str(aliases.get(token, token)).strip().lower()
    if resolved in plans:
        return resolved
    return default_plan if default_plan in plans else "community"


def plan_summary(catalog: dict[str, Any], plan: str) -> dict[str, Any]:
    plans = catalog.get("plans", {})
    row = plans.get(plan, {}) if isinstance(plans, dict) else {}
    if not isinstance(row, dict):
        row = {}
    return {
        "plan": plan,
        "display_name": str(row.get("display_name", plan.replace("_", " ").title())),
        "price_monthly_usd": float(row.get("price_monthly_usd", 0.0) or 0.0),
        "billing_mode": str(row.get("billing_mode", "saas")),
        "description": str(row.get("description", "")),
        "features": [str(item) for item in list(row.get("features", []))],
        "limits": dict(row.get("limits", {})) if isinstance(row.get("limits"), dict) else {},
    }


def marketplace_commission(catalog: dict[str, Any], gross_amount_usd: float) -> dict[str, float]:
    marketplace = catalog.get("marketplace", {})
    rate = 0.25
    if isinstance(marketplace, dict):
        try:
            rate = float(marketplace.get("commission_rate", 0.25))
        except (TypeError, ValueError):
            rate = 0.25
    normalized_rate = min(max(rate, 0.0), 1.0)
    gross = max(float(gross_amount_usd), 0.0)
    commission = round(gross * normalized_rate, 2)
    seller_net = round(gross - commission, 2)
    return {
        "commission_rate": normalized_rate,
        "gross_amount_usd": gross,
        "commission_amount_usd": commission,
        "seller_net_amount_usd": seller_net,
    }


def _resolve_stripe_price_id(settings: APISettings, plan: str, catalog: dict[str, Any]) -> str:
    direct = {
        "starter_cloud": settings.stripe_price_starter,
        "pro_cloud": settings.stripe_price_pro,
        "enterprise": settings.stripe_price_enterprise,
    }.get(plan, "")
    if str(direct).strip():
        return str(direct).strip()
    plans = catalog.get("plans", {})
    if not isinstance(plans, dict):
        return ""
    row = plans.get(plan, {})
    if not isinstance(row, dict):
        return ""
    env_key = str(row.get("stripe_price_env", "")).strip()
    if not env_key:
        return ""
    return str(os.getenv(env_key, "")).strip()


def create_checkout_session(
    *,
    settings: APISettings,
    catalog: dict[str, Any],
    workspace_id: str,
    plan: str,
    customer_email: str,
    success_url: str,
    cancel_url: str,
    metadata: dict[str, Any] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    provider = str(settings.billing_provider).strip().lower() or "demo"
    price_id = _resolve_stripe_price_id(settings, plan, catalog)
    if dry_run or provider != "stripe" or not settings.stripe_secret_key or not price_id:
        session_id = f"demo_checkout_{hashlib.sha256(f'{workspace_id}:{plan}'.encode('utf-8')).hexdigest()[:12]}"
        return {
            "provider": provider,
            "live": False,
            "dry_run": True,
            "session_id": session_id,
            "checkout_url": f"https://billing.pqts.local/checkout/{session_id}",
            "price_id": price_id or "",
        }

    response = requests.post(
        "https://api.stripe.com/v1/checkout/sessions",
        auth=(settings.stripe_secret_key, ""),
        data={
            "mode": "subscription",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": "1",
            "customer_email": customer_email,
            "metadata[workspace_id]": workspace_id,
            "metadata[plan]": plan,
            **{
                f"metadata[{key}]": str(value)
                for key, value in dict(metadata or {}).items()
                if str(key).strip()
            },
        },
        timeout=15.0,
    )
    payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
    if not bool(200 <= int(response.status_code) < 300):
        detail = str(payload.get("error", {}).get("message", response.text[:200])) if isinstance(payload, dict) else response.text[:200]
        raise RuntimeError(f"stripe_checkout_failed status={response.status_code} detail={detail}")
    return {
        "provider": provider,
        "live": True,
        "dry_run": False,
        "session_id": str(payload.get("id", "")),
        "checkout_url": str(payload.get("url", "")),
        "price_id": price_id,
    }


def build_workspace_subscription(
    *,
    workspace_id: str,
    plan: str,
    actor: str,
    catalog: dict[str, Any],
    status: str = "active",
    trial_days: int = 0,
) -> dict[str, Any]:
    summary = plan_summary(catalog, plan)
    now = datetime.now(timezone.utc)
    trial_ends_at = ""
    if int(trial_days) > 0 and status in {"trialing", "active"}:
        trial_ends_at = (now + timedelta(days=int(trial_days))).isoformat()
    return {
        "workspace_id": workspace_id,
        "plan": plan,
        "status": status,
        "price_monthly_usd": summary["price_monthly_usd"],
        "currency": "USD",
        "billing_mode": summary["billing_mode"],
        "trial_ends_at": trial_ends_at,
        "updated_at": now.isoformat(),
        "updated_by": actor,
    }
