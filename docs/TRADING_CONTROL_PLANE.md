# Trading Control Plane

Last updated: 2026-05-27 (America/Denver)

PQTS now treats manual orders, agent proposals, and strategy/autopilot orders as the same governed object: an `OrderIntent`. The intent can be proposed, simulated, approved, and prepared for router submission, but the only runtime order-entry path remains `TradingEngine.submit_order_intent()` -> `RiskAwareRouter.submit_order()`.

## Modes

- `manual`: human order intents only; strategies and agents cannot auto-submit.
- `assisted_manual`: human-led trading with agent proposals; operator approval is still required.
- `paper_autopilot`: strategies may submit paper intents; human/agent intents require approval.
- `live_canary`: tiny live allocation only after explicit approval, sync health, and kill-switch checks.
- `live_autopilot`: approved live autopilot only; agent self-execution remains blocked.
- `kill_only`: no new risk; only approved emergency reduce-only sells/flatten actions.

## Order Intent Contract

Required core fields:

- `order_id`
- `strategy_id`
- `symbol`
- `side`
- `quantity`
- `order_type`
- `requested_price`
- `expected_alpha_bps`

Control fields:

- `source`: `human`, `agent`, `strategy`, or `emergency`
- `mode`: one of the trading modes above
- `approval_status`: `proposed`, `simulated`, `approved`, `auto_approved`, `rejected`, `submitted`
- `risk_budget_pct`
- `reduce_only`
- `reason`
- `metadata`

## API Flow

1. `GET /v1/trading/modes`
2. `PUT /v1/trading/mode`
3. `POST /v1/trading/order-intents`
4. `POST /v1/trading/order-intents/{intent_id}/simulate`
5. `POST /v1/trading/order-intents/{intent_id}/approve`
6. `POST /v1/trading/order-intents/{intent_id}/submit`

The API `submit` step does not place an order. It marks the intent `ready_for_router` and returns the exact router submission contract. Runtime execution still happens only through `TradingEngine.submit_order_intent()`, which re-checks the mode/approval gates and then calls `RiskAwareRouter.submit_order()`.

## Steering

Steering actions are recorded through:

- `GET /v1/trading/steering-actions`
- `POST /v1/trading/steering-actions`

Supported actions:

- `pause_strategy`
- `resume_strategy`
- `exclude_symbol`
- `include_symbol`
- `set_risk_budget`
- `force_paper_only`
- `set_mode`
- `kill_only`
- `flatten_symbol`
- `flatten_all`

Agents can propose steering only when their policy has `steer=true`. Privileged steering actions such as `set_mode`, `kill_only`, and flattening require an operator/admin role.

## Safety Contract

- No API path directly instantiates exchange adapters.
- No API path directly places a live order.
- Live modes fail closed on kill-switch or brokerage sync-health blocks.
- Agents cannot self-execute orders; operator approval is required.
- `kill_only` admits only emergency reduce-only sell intents.
