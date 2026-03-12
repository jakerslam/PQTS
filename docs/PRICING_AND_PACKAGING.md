# Pricing And Packaging

Last updated: 2026-03-12 (America/Denver)

## Product Model

PQTS monetization follows an **open-core + cloud + verified marketplace** model:

1. Community core remains MIT and self-hosted.
2. Managed cloud, support, and governance workflows are paid.
3. Marketplace revenue compounds through verified strategy distribution.

## Plan Matrix

| Plan | Price | Positioning | Core Limits |
|---|---:|---|---|
| Community | $0 | Local-first learning and paper-first safety | No managed hosting, no paid SLA |
| Starter Cloud | $49/mo | Hosted onboarding with baseline monitoring | 1 live strategy slot |
| Pro Cloud | $299/mo | Serious solo/team operators with advanced analytics | Unlimited strategies, priority support |
| Enterprise | $999+/mo or annual | Compliance, custom controls, and dedicated support | Custom contracts and self-hosted options |

Canonical machine-readable source:
- `config/monetization/plan_catalog.json`

## Marketplace

- Verified strategy marketplace commission: **25%** (`commission_rate=0.25`).
- Verified badge policy remains tied to promotion-gate evidence and trust labels.
- Marketplace economics are surfaced through API revenue summaries.

## Self-Serve API Surface

- `POST /v1/signup`
- `POST /v1/workspaces/{workspace_id}/billing/subscribe`
- `POST /v1/workspaces/{workspace_id}/campaign/start`
- `GET /v1/workspaces/{workspace_id}/ops-health`
- `GET /v1/workspaces/{workspace_id}/promotion-gate`
- `POST /v1/marketplace/sales/record`
- `GET /v1/marketplace/revenue-summary`

## Stripe Integration (Provider-Ready)

Billing provider is runtime-configurable:

- `PQTS_BILLING_PROVIDER=demo|stripe`
- `PQTS_STRIPE_SECRET_KEY`
- `PQTS_STRIPE_PUBLISHABLE_KEY`
- `PQTS_STRIPE_WEBHOOK_SECRET`
- `PQTS_STRIPE_PRICE_STARTER`
- `PQTS_STRIPE_PRICE_PRO`
- `PQTS_STRIPE_PRICE_ENTERPRISE`

Safety default:
- API checkout creation runs in `dry_run` mode unless explicitly disabled.

## Revenue Streams

1. Cloud subscriptions (Starter/Pro/Enterprise).
2. Verified strategy marketplace commissions.
3. Enterprise self-hosted contracts with SLA/support.
4. Professional services (onboarding/integration/audit support).
5. Exchange partnership/referral overlays (separate human-governed track).

## Packaging Guardrails

- No promises of returns; claims must link to reproducible artifacts.
- Live-capital enablement remains promotion-gated and fail-closed.
- Community messaging stays paper-first and education-first.
- Paid messaging emphasizes reliability, governance, and operator ergonomics.
