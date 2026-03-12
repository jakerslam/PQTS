# Self-Serve Signup Spec

Last updated: 2026-03-12 (America/Denver)

## Objective

Allow pilot users and teams to self-onboard into PQTS with safe defaults, billing-aware entitlement assignment, and immediate paper-campaign continuity.

## Implemented API Contracts

1. `POST /v1/signup`
2. `POST /v1/workspaces/{workspace_id}/billing/subscribe`
3. `POST /v1/workspaces/{workspace_id}/campaign/start`
4. `GET /v1/workspaces/{workspace_id}/ops-health`
5. `GET /v1/workspaces/{workspace_id}/promotion-gate`
6. `POST /v1/marketplace/sales/record`
7. `GET /v1/marketplace/revenue-summary`

## Signup Flow

1. User submits `email`, `organization`, `plan`.
2. User must accept both:
   - `accepted_risk_disclaimer=true`
   - `accepted_paper_first_policy=true`
3. API creates:
   - workspace identity
   - feature flags based on plan
   - subscription record (community active, paid plans trialing by default)

## Billing Subscription Flow

1. User selects target plan.
2. API resolves plan aliases via `config/monetization/plan_catalog.json`.
3. If paid plan + checkout requested:
   - create checkout session (`dry_run` default true)
   - Stripe mode available via provider switch
4. Workspace plan + feature flags update atomically with subscription status.

## Campaign Start Flow

1. Workspace can trigger bounded paper campaign.
2. Default mode is `dry_run` with explicit command output.
3. Execution mode (`execute=true`) runs the same deterministic script path used elsewhere.
4. Paper-first policy is always explicit in response payload.

## Ops + Promotion Surfaces

- Ops health surfaces risk state, sync health, incidents, and kill-switch.
- Promotion gate surface emits stage status and pass/fail reasons for strategy progression.

## Non-Goals (Current Slice)

- Automated Stripe webhook reconciliation pipeline.
- Marketplace payout disbursement integration (currently accounting-level records only).
- Multi-org delegated RBAC and billing hierarchies.
