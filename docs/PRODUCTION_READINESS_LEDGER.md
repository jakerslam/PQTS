# Production Readiness Ledger

Last updated: 2026-05-28 (America/Denver)

Refs: `PGQ-1` through `PGQ-26`

Production status: `not production approved for live auto trading`.

This ledger is the working checklist for turning PQTS into a serious production quant system. A row is production-ready only when the evidence column points to runnable checks, generated artifacts, or operator-approved records.

## Ledger

| Capability | Refs | Status | Evidence | Open risk | Release gate |
| --- | --- | --- | --- | --- | --- |
| Three governed control modes | `PGQ-1`, `PGQ-2` | Partial | `src/core/trading_control.py`, `docs/TRADING_CONTROL_PLANE.md` | Product names and runtime modes need one policy matrix. | Mode policy loads fail-closed and is tested. |
| Single router-only capital path | `PGQ-3`, `PGQ-11` | Partial | `TradingEngine.submit_order_intent()`, `RiskAwareRouter.submit_order()`, `tests/test_enforcement.py` | More runtime surfaces must be covered by regression tests. | User, agent, and auto tests prove router-only execution. |
| Order intent lifecycle | `PGQ-4` | Partial | `src/contracts/execution_flow.py`, API order-intent flow | Lifecycle is not yet a single immutable transition ledger. | Every transition has actor, timestamp, prior/new state, reason, evidence. |
| User-directed trading surface | `PGQ-5` | Partial | API order-intent simulation/approval flow | UI/operator surface still needs full pre-trade risk and cost display. | Manual order cannot route without approval and risk impact preview. |
| Agent proposal queue | `PGQ-6`, `PGQ-8`, `PGQ-16` | Partial | `src/core/trading_control.py`, `src/core/agent_proposal_store.py`, `services/api/routes/core.py`, `tests/test_trading_control.py`, `tests/test_agent_proposal_store.py`, `tests/test_services_api_rest_endpoints.py` | API/operator surface exists; still needs UI workflow and persistence promotion from JSONL to production DB where configured. | Proposals require evidence, expiry, gate checks, risk impact, operator approval, replayable decision events, and materialize only approved `OrderIntent`s. |
| Autonomous strategy constraints | `PGQ-7`, `PGQ-18`, `PGQ-19` | Partial | stage-gate APIs, autopilot policy pack | Order-time stage eligibility must be enforced for auto/live paths. | Auto mode admits only stage-promoted strategies within budgets. |
| Immutable decision ledger | `PGQ-8`, `PGQ-21` | Partial | `OpsEventStore`, agent receipts, order truth artifacts | Multiple ledgers are not yet unified/replayable end to end. | Proposal-to-fill replay reconstructs all decisions and risk gates. |
| Production data plane | `PGQ-9`, `PGQ-14` | Started | `src/adapters/prediction_market_*`, `src/research/prediction_market_microstructure.py`, `src/research/prediction_market_capture.py`, `src/research/prediction_market_replay.py`, `scripts/capture_prediction_market_snapshots.py`, `scripts/build_prediction_market_replay.py`, `tests/test_prediction_market_capture.py` | Need entitlement manifests, longer real feed captures, and order/trade/resolution joins. | Raw order book/trade/resolution data can replay features point-in-time. |
| Point-in-time feature store | `PGQ-10` | Started | prediction-market microstructure feature builder, CLI, and replay manifest tests | Feature manifest exists for JSONL replay; needs registry/promotion integration. | Feature snapshots include lineage, schema, source, hashes, and quality flags. |
| Execution-realistic simulation | `PGQ-12` | Partial | paper fill model, microstructure simulation controls | Prediction-market queue/impact replay needs real trade/book data. | Simulator models costs, liquidity, partial fills, latency, rejects, and rate limits. |
| Research validation gates | `PGQ-13` | Partial | real-money validation reports, walk-forward/autopsy tools | Current tested strategies remain HOLD; no deployable alpha yet. | OOS, purged CV, overfit controls, robustness, and costs all pass. |
| Alpha source program | `PGQ-14`, `PGQ-25` | Started | prediction-market/microstructure module | Need falsifiable research cards and replay datasets. | At least one non-OHLCV alpha card passes evidence thresholds. |
| Agent role separation | `PGQ-15`, `PGQ-17` | Partial | agent policy/intent APIs, Ollama pilot scaffolding | Challenger A/B metrics not yet running continuously. | Agents remain challenger until they improve net evidence without hard-control violations. |
| Paper/canary/live ladder | `PGQ-18`, `PGQ-19`, `PGQ-26` | Partial | promotion records and gate evaluation APIs | Human venue/legal approval blocks live prediction-market trading. | No stage skips; paper and canary evidence thresholds are met. |
| Operations and observability | `PGQ-20` | Partial | ops events, sync health, incident controls | Need complete dashboards/alerts for proposal state and mode health. | Daily/weekly operator checklist has live metrics and degraded states. |
| Reconciliation and TCA | `PGQ-21` | Partial | reconciliation daemon, TCA feedback components | Need venue-wide coverage and promotion blocking on breaks. | Breaks block promotion and can downgrade/flatten by severity. |
| Incident and disaster controls | `PGQ-22` | Partial | kill-switch/manual halt controls | Emergency action catalog needs rehearsed drills for each environment. | Cancel/flatten/disable/downgrade/revoke controls are idempotent and tested. |
| Security, secrets, deployments | `PGQ-23` | Partial | live secret validation, environment configs | Production auth/TLS/CORS/rate-limit posture must be reverified before ingress. | Research/paper/canary/live environments are separated with scoped credentials. |
| Production readiness ledger | `PGQ-24` | Started | this file | Needs CI freshness/checklist enforcement. | Ledger rows cannot be marked ready without evidence and tests. |

## Acceptance Checklist

- [ ] `make codex-enforcer` passes.
- [ ] `make assimilation-66-71-check` passes.
- [ ] `pytest -q tests/test_enforcement.py` passes.
- [ ] `pytest -q tests/test_trading_control.py tests/test_core_engine_order_intents.py` passes.
- [ ] `pytest -q tests/test_prediction_market_microstructure.py` passes.
- [ ] Control-mode policy matrix exists and fails closed when missing or invalid.
- [x] Agent proposal queue has durable append-only core ledger and replay tests.
- [x] Agent proposal queue is connected to API/operator approval surfaces.
- [ ] No live-capable route can execute without `TradingEngine.submit_order_intent()`.
- [x] Prediction-market raw snapshots have JSONL replay manifests with content hashes.
- [x] Prediction-market raw snapshot capture has a CLI, append-only manifest contract, and Polymarket active-book discovery path.
- [x] Prediction-market replay manifests can be built by CLI with row-count and quality-flag gates.
- [x] Feature builder is point-in-time and excludes future resolution labels from feature artifacts.
- [ ] At least one prediction-market/microstructure alpha card exists and passes quality threshold.
- [ ] Strategy promotion requires OOS, walk-forward, robustness, costs, capacity, and regime evidence.
- [ ] Paper trading has sufficient duration/fill sample and TCA drift below threshold.
- [ ] Live canary legal/account/venue eligibility has human approval.
- [ ] Emergency cancel/flatten/downgrade/revoke drills pass in paper/canary environments.
- [ ] Reconciliation breaks block promotion and emit operator-visible incidents.
- [ ] Agent challenger A/B metrics prove no increase in hard-control violations.

## Current Operator Note

The system has useful bones: router-only execution enforcement, a typed `OrderIntent`, promotion APIs, prediction-market adapters, durable agent proposal events with API approval/materialization, and microstructure controls. It is not yet a proven money printer. The next high-leverage work is building real prediction-market order-book replay and feature manifests, not more OHLCV parameter search.
