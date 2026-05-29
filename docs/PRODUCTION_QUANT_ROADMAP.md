# Production Quant Roadmap

Last updated: 2026-05-28 (America/Denver)

Refs: `PGQ-1` through `PGQ-26`

Current classification: `not production approved for live auto trading`.

This roadmap turns PQTS into production-grade quant software that can operate in three governed control modes: user-directed, agent-steered, and autonomous. The plan borrows useful patterns from LEAN, NautilusTrader, Freqtrade, Qlib/FinRL-style research separation, and multi-agent trading systems, but every borrowed pattern is subordinated to PQTS hard safety controls.

## Non-Negotiable Contract

All capital-affecting actions must flow through:

1. Signal, human request, or agent proposal.
2. `OrderIntent`.
3. deterministic control/risk gate.
4. operator approval when required.
5. `TradingEngine.submit_order_intent()`.
6. `RiskAwareRouter.submit_order()`.
7. adapter execution, reconciliation, and TCA.

No agent, strategy, notebook, API route, or UI may instantiate venue adapters directly or place orders outside `RiskAwareRouter`.

## Control Modes

| Product mode | Runtime mapping | Allowed behavior | Acceptance gate |
| --- | --- | --- | --- |
| User-directed | `manual` | Human-originated intents only, explicit approval before routing. | Approved manual intent reaches router; unapproved intent is rejected before router. |
| Agent-steered | `assisted_manual` | Agents propose trades, hedges, promotions, demotions, and steering; operators approve. | Agent proposal queue enforces required fields, expiry, no self-approval, and approved intent still routes only via router. |
| Autonomous | `paper_autopilot`, `live_canary`, `live_autopilot` | Stage-promoted strategies may create bounded intents. | Strategy intent is accepted only under mode/risk/stage policy and still reaches execution only through router. |

## Roadmap Phases

### Phase 0: Router-Only Control Plane

Refs: `PGQ-1`, `PGQ-2`, `PGQ-3`, `PGQ-4`, `PGQ-5`, `PGQ-6`, `PGQ-7`, `PGQ-8`, `PGQ-16`

Deliverables:
- Machine-readable control-mode policy.
- Agent proposal queue and approval contract.
- Lifecycle states for proposals and order intents.
- Tests proving user, agent-steered, and auto flows cannot bypass `RiskAwareRouter`.
- Decision ledger entries for proposals, approvals, rejections, mode changes, order submissions, and emergency actions.

Acceptance gates:
- `pytest -q tests/test_trading_control.py tests/test_core_engine_order_intents.py` passes.
- `pytest -q tests/test_enforcement.py` passes.
- No source file outside `src/execution/risk_aware_router.py` defines `submit_order()`.
- No production route directly calls adapter order methods.

### Phase 1: Real Alpha Data Plane

Refs: `PGQ-9`, `PGQ-10`, `PGQ-14`, `PGQ-25`

Deliverables:
- Immutable raw stores for prediction-market snapshots, order books, trades, resolution metadata, fees, liquidity, and settlement events.
- Point-in-time feature builder for prediction-market microstructure: implied probability, spread, parity gap, depth imbalance, liquidity, velocity, staleness, and quality flags.
- Dataset manifests with source, entitlement, timestamp, schema version, and code/config hash.
- Replay fixtures for Polymarket/Kalshi-style event markets before any strategy promotion.

Acceptance gates:
- Feature rows never include future resolution labels.
- Data gaps, stale books, invalid quotes, and sequence breaks force `hold` or no-trade behavior.
- Replay can rebuild a feature snapshot from raw data and a manifest.
- At least one alpha card states a falsifiable prediction-market/microstructure hypothesis with costs and failure modes.

### Phase 2: Execution-Realistic Research Validation

Refs: `PGQ-11`, `PGQ-12`, `PGQ-13`, `PGQ-18`, `PGQ-19`

Deliverables:
- Single strategy contract across research, backtest, shadow, paper, canary, and live.
- Purged/walk-forward validation with deflated Sharpe or equivalent multiple-testing control.
- Parameter-neighborhood robustness and regime robustness.
- Execution simulator with fees, spread, slippage, depth, partial fills, latency, rejects, rate limits, and queue assumptions.

Acceptance gates:
- Backtest-to-paper promotion requires OOS evidence, walk-forward pass, cost realism, capacity check, and no unresolved high-severity data defects.
- Single-window Sharpe and OHLCV-only curve fits are insufficient.
- Strategy reports explicitly label unmodeled assumptions.

### Phase 3: Paper and Shadow Operations

Refs: `PGQ-18`, `PGQ-19`, `PGQ-20`, `PGQ-21`

Deliverables:
- Shadow signal mode with no capital impact.
- Paper mode using the same order-intent, risk, sizing, and router contracts.
- TCA comparing simulated vs realized paper fills.
- Daily operator workflow for slippage drift, kill-switch events, reconciliation breaks, and active candidates.

Acceptance gates:
- Minimum paper duration and fill count are met.
- Slippage MAPE and reject rate are within tolerance.
- No unresolved reconciliation breaks.
- Expected-vs-realized alpha remains stable after costs.

### Phase 4: Live Canary

Refs: `PGQ-7`, `PGQ-18`, `PGQ-19`, `PGQ-21`, `PGQ-22`, `PGQ-23`, `PGQ-26`

Deliverables:
- Environment-separated live canary deployment.
- Least-privilege credentials.
- Canary capital budgets, venue allowlists, max daily loss, max drawdown, max concentration, and kill switches.
- Emergency controls: cancel all, flatten, disable venue, disable strategy, downgrade mode, pause proposals, revoke external endpoint.

Acceptance gates:
- Legal/account/venue eligibility is approved by a human reviewer.
- Canary uses tiny capital and cannot expand automatically.
- No hard-limit violations across the canary window.
- Recovery from emergency state requires explicit health revalidation.

### Phase 5: Limited Live and Agent Challenger

Refs: `PGQ-15`, `PGQ-16`, `PGQ-17`, `PGQ-20`, `PGQ-26`

Deliverables:
- Agent roles separated into hypothesis, data QA, implementation, skeptic/risk, sizing, execution/TCA monitor, and operator summarizer.
- Challenger A/B between deterministic autopilot and agent-assisted recommendations.
- Metrics: net OOS Sharpe differential, net PnL after costs, false-promotion rate, slippage MAPE, drawdown events, hard-control violations, and kill-switch frequency.

Acceptance gates:
- Agent steering does not become default unless it improves net evidence without increasing hard-control violations.
- Any agent output missing required decision fields is invalid.
- Agents may recommend and steer, but never route capital directly.

## Production Acceptance

PQTS can be called production-grade auto-trading software only when all of the following are true:

- All three control modes operate through one audited order-intent/router path.
- Backtest, paper, and live strategy parity is demonstrated.
- Data and feature snapshots are reproducible from raw data manifests.
- Reconciliation and TCA are live for all routed venues.
- Emergency controls are tested and recoverable.
- At least one strategy passes research, paper, and live canary gates without hard-control violations.
- `docs/PRODUCTION_READINESS_LEDGER.md` contains evidence for every required capability.
