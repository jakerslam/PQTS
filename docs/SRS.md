# Software Requirements Specification (SRS)

## 1. Purpose

Define requirements for integrating a prediction-market strategy into PQTS based on a transferable core idea:

- Buy underdogs only when the market is likely mispriced and expected value (EV) is positive after costs.

This captures usable signal logic from a public strategy discussion while avoiding blind copy-trading.

## 2. Scope

In scope:

- Underdog mispricing signal generation.
- EV-based entry gating.
- Position sizing and portfolio limits.
- Risk and observability controls.
- Backtest and paper-trading validation.

Out of scope:

- Wallet-copying as a primary source of alpha.
- Any strategy that depends on private/non-public information.

## 3. Strategy Summary

The strategy targets binary/event markets where crowd behavior overprices favorites.

Core concept:

- Let `p_market` be implied market probability for an outcome.
- Let `p_model` be model-estimated fair probability.
- Let `edge = p_model - p_market`.
- Enter only when `edge` and net EV exceed configured thresholds, with an underdog constraint (`p_market < 0.50` by default).

## 4. Functional Requirements

### FR-1 Market Probability Normalization

- System shall convert venue prices/orderbook quotes into normalized implied probabilities.
- System shall support YES/NO binary outcome normalization.
- System shall record the exact quote timestamp and venue source used for each signal.

### FR-2 Fair Probability Estimation

- System shall compute `p_model` using configurable model pipelines (baseline calibration model required).
- System shall expose per-market calibration quality metrics (Brier score, calibration error).
- System shall reject signals from models failing minimum calibration thresholds.

### FR-3 Underdog Mispricing Signal

- System shall define underdog candidates as outcomes with `p_market < underdog_max_prob` (default `0.50`).
- System shall generate a candidate signal only if:
  - `edge >= min_edge`,
  - net EV after fees/slippage > `min_net_ev`,
  - liquidity and capacity constraints are satisfied.

### FR-4 Profitability Gate Integration

- System shall integrate with existing profitability gating mechanisms.
- System shall block orders when expected net alpha is non-positive under configured execution cost assumptions.
- System shall log blocked signals with explicit reason codes.

### FR-5 Position Sizing

- System shall size positions using fractional Kelly (configurable fraction, default half-Kelly).
- System shall enforce per-market and per-event max exposure caps.
- System shall enforce per-strategy gross notional and drawdown-aware throttling.

### FR-6 Portfolio Constraints

- System shall cap correlated exposures across similar events/leagues/time windows.
- System shall enforce strategy-level and portfolio-level risk limits already present in PQTS.
- System shall support dynamic strategy disable when rolling realized edge becomes negative beyond threshold.

### FR-7 Exit and Lifecycle Rules

- System shall support explicit exit rules:
  - price converges to fair value,
  - stop-loss/time-stop reached,
  - event resolution,
  - risk manager forced unwind.
- System shall persist signal metadata through order lifecycle for attribution.

### FR-8 Telemetry and Attribution

- System shall emit signal-level telemetry:
  - `p_market`, `p_model`, `edge`, expected EV, fees/slippage estimate, decision outcome.
- System shall emit realized-vs-expected EV diagnostics.
- System shall support per-league/per-market attribution rollups.

## 5. Non-Functional Requirements

### NFR-1 Latency

- Paper mode signal computation latency target: `<= 500 ms` per market snapshot.

### NFR-2 Reliability

- Strategy must degrade safely (no order emission) on stale or incomplete market data.
- All blocked/error paths must be auditable.

### NFR-3 Determinism

- Backtest and paper simulation runs shall be reproducible with fixed seeds and fixed data snapshots.

## 6. Data Requirements

Minimum data fields:

- market/event ID
- outcome ID
- quote price and side
- timestamp (UTC)
- venue identifier
- realized resolution label (for supervised evaluation)
- optional context features (league, start time, market depth, spread, liquidity)

## 7. Validation and Acceptance Criteria

### AC-1 Backtest Readiness

- Strategy must pass walk-forward backtests with:
  - positive net expectancy after modeled costs,
  - stable calibration in holdout windows,
  - max drawdown within configured risk tolerance.

### AC-2 Paper-Trade Readiness

- Strategy must pass paper campaign gates:
  - positive realized net alpha over minimum sample size,
  - no critical risk/compliance violations,
  - expected-vs-realized slippage error within tolerance.

### AC-3 Promotion Gate

- Live canary promotion requires:
  - paper campaign pass,
  - no unresolved high-severity incidents,
  - portfolio-level risk limits intact under stress replay.

## 8. Risks and Controls

Identified risks:

- Survivorship bias from single-wallet anecdotes.
- Regime shifts causing probability model drift.
- Liquidity/impact degrading theoretical EV.

Required controls:

- Cross-period validation, not single-window optimization.
- Ongoing calibration and drift monitoring with auto-throttle/disable.
- Conservative sizing and strict net-EV gating.

## 9. Existing Functional Baseline (Regression Guard)

The following baseline items are already implemented in PQTS and shall remain functional when adding or modifying strategy logic.

### BF-1 Runtime Configuration and Boot Controls

- System shall validate engine config schema and required risk capital fields before startup.
- System shall hydrate `${VAR}` secrets from supported secret backends (`env`, `file_json`, `aws_sm`).
- System shall enforce live-mode secret policy checks before allowing live operation.
- System shall apply mechanism switches deterministically to execution features.
- System shall persist and recover engine state (positions/orders/history) across restarts.
- System shall perform graceful shutdown with pending-order cancel and position flatten routines.

### BF-2 Market/Strategy Control Plane

- System shall support runtime market/strategy toggles and profile-based activation.
- System shall validate strategy contracts (name, market scope, risk budget, max positions).
- System shall enforce operator-tier limits (`simple` vs `pro`) for runtime overrides.
- System shall support autopilot modes (`manual`, `auto`, `hybrid`) with deterministic scoring.
- System shall enforce autopilot policy packs (allowed list, min/max active strategies).
- System shall enforce tenant entitlements (markets, strategy allowlist, live-trading permission, min/max strategy count).

### BF-3 Mandatory Order and Risk Pipeline

- System shall route all orders through `RiskAwareRouter` and shall not permit bypass paths.
- System shall evaluate kill-switch decisions (`ALLOW`, `REDUCE`, `HALT`, `FLATTEN`) pre-trade.
- System shall enforce live idempotency controls for duplicate order intent prevention.
- System shall enforce venue/endpoint rate limits with retry metadata.
- System shall support scoped strategy disable controls (strategy, strategy+venue, strategy+symbol, strategy+venue+symbol).
- System shall apply profitability gate checks before order placement.
- System shall support capacity-curve throttling/blocking decisions.
- System shall support confidence-weighted allocation controls.
- System shall support regime overlay throttling and strategy blocking.
- System shall enforce shorting controls before execution.
- System shall support routing failover under venue degradation conditions.
- System shall record immutable order-ledger entries and TCA feedback records for every execution attempt.

### BF-4 Market Data and Reliability Controls

- System shall gate execution on market-data quality metrics (completeness, drift, feature parity).
- System shall support market-data resilience controls (stale-feed detection, failover quotes, replay window fallback).
- System shall support deterministic websocket reconnection/backoff tracking.
- System shall support internal-vs-venue reconciliation diffing with tolerance thresholds.

### BF-5 Research, Simulation, and Ops Automation

- System shall provide event-driven backtesting with commission/slippage modeling.
- System shall provide simulation-suite execution with per-scenario telemetry and optimization leaderboard artifacts.
- System shall support campaign/promotion/canary operational flows via existing scripts.
- System shall support one-command world-class ops checklist orchestration and consolidated reporting.

### BF-6 Security, Compliance, and Data Governance

- System shall support compliance/security validation and reporting flows.
- System shall support data-retention enforcement for analytics/artifact stores.
- System shall support secret rotation validation when configured.
- System shall support PnL truth-ledger workflows for strategy performance governance.

## 10. Regression Verification Matrix

The following verification matrix is required for any change touching strategy, execution, risk, or runtime control paths.

### RV-1 Core Control Plane

- `pytest tests/test_toggle_controls.py tests/test_strategy_contracts.py tests/test_autopilot_mode.py tests/test_autopilot_policy.py tests/test_multi_tenant.py tests/test_operator_tier.py`

### RV-2 Execution and Risk Overlay

- `pytest tests/test_profitability_controls.py tests/test_kill_switches.py tests/test_market_data_resilience.py tests/test_live_ops_controls.py tests/test_confidence_allocator.py tests/test_capacity_curves.py tests/test_shorting_controls.py tests/test_router_live_ops_guards.py`

### RV-3 Runtime Integrity and Security

- `pytest tests/test_engine_shutdown_persistence.py tests/test_order_ledger.py tests/test_tca_feedback_loop.py tests/test_config_validation.py tests/test_secret_manager.py tests/test_secrets_policy.py tests/test_validate_live_secrets_cli.py`

### RV-4 Simulation and Ops Flow

- `pytest tests/test_simulation_suite.py tests/test_simulation_telemetry.py tests/test_promotion_gates.py tests/test_run_world_class_ops_cli.py tests/test_run_canary_ramp_cli.py tests/test_run_paper_campaign_cli.py`

## 11. Implementation Notes for PQTS

- Introduce strategy ID: `underdog_value`.
- Add config fields under `strategies.underdog_value` and execution EV gates.
- Reuse existing PQTS components: strategy contract validation, risk manager, profitability gate, attribution, and telemetry pipelines.
- Any rollout of `underdog_value` shall satisfy Section 10 regression verification before promotion.

## 12. Additional Requirements from External Post Chain (March 8, 2026)

These requirements were extracted from the referenced X post and its included links. They are additive and must still satisfy all baseline controls in Sections 9-11.

### XR-1 Short-Cycle Binary Arbitrage Scanner

- System shall support continuous scanning of short-cycle binary markets (default intervals: `5m`, `15m`).
- System shall compute two-leg bundle edge for each market:
  - `bundle_edge = 1.0 - (ask_yes + ask_no) - fee_buffer - slippage_buffer`.
- System shall emit a bundle arbitrage signal only when:
  - `bundle_edge >= min_bundle_edge`,
  - both legs satisfy minimum depth/liquidity constraints,
  - quote age is within stale-data limit.

### XR-2 Legging/Execution Safety for Two-Leg Trades

- System shall prefer atomic or tightly coupled execution for YES/NO pair entries.
- If atomic pairing is unavailable, system shall enforce:
  - max legging time,
  - max unhedged notional,
  - forced unwind/hedge path for orphaned legs.

### XR-3 Venue Universe and Market-Type Configuration

- System shall allow explicit configuration of short-cycle universe by:
  - asset (e.g., BTC, ETH, SOL, XRP),
  - venue market family (e.g., up/down interval markets),
  - interval bucket (`5m`, `15m`).
- System shall support disabling any interval/asset bucket independently at runtime.

### XR-4 Micro-Edge Throughput Accounting

- System shall report batch-level and rolling metrics for micro-edge execution:
  - opportunities detected,
  - opportunities executed,
  - fill rate,
  - reject rate,
  - realized edge per trade,
  - cumulative net alpha after costs.
- System shall auto-throttle or disable when realized edge persistence falls below configured floor.

### XR-5 Optional Asymmetric Single-Leg Mode

- System may support an optional single-leg mode for asymmetric opportunities.
- Single-leg mode shall remain disabled by default.
- When enabled, single-leg trades shall pass all existing profitability, confidence, capacity, shorting, and kill-switch controls.

### XR-6 Automation Security Hardening (Linked Setup Thread)

- System shall require private control-plane access only (no public administrative ingress by default).
- System shall enforce operator allowlisting for bot command channels.
- System shall support command allowlists and sandbox/container isolation for risky operations.
- System shall require least-privilege integration tokens/scopes for external providers.
- System shall block promotion when security health checks fail.

### XR-7 Provenance and Confidence Handling

- System documentation shall label externally sourced claims as:
  - `observed` (directly visible in linked artifacts),
  - `inferred` (derived from behavior/log snippets),
  - `unverified` (marketing/performance claims without reproducible data).
- Promotion decisions shall rely only on `observed`/`inferred` items that pass Section 10 verification.

## 13. Additional Requirements from External Post (DeFiMinty, March 8, 2026)

These requirements are derived from the referenced Hyperliquid “squeeze radar” post and attached status screenshot.

### HM-1 Universe-Scale Squeeze Monitoring

- System shall support scanning all configured assets in a target venue universe (e.g., Hyperliquid perps).
- System shall expose ingestion health telemetry at runtime:
  - assets tracked,
  - websocket connection state,
  - event throughput over rolling window (for example events/30s).

### HM-2 Multi-Factor Squeeze Feature Set

- System shall compute squeeze features at minimum from:
  - funding-rate regime and funding-rate change,
  - volume spike intensity vs rolling baseline,
  - open-interest delta and acceleration,
  - options IV/skew features where available.
- System shall permit venue-specific feature fallback when options data is unavailable.

### HM-3 Composite Scoring and Ranking

- System shall compute a composite squeeze score per asset from normalized feature contributions.
- System shall publish ranked `top_n` assets by composite score each cycle.
- System shall log score components for attribution/debugging (not only final score).

### HM-4 Alerting Pipeline

- System shall support alert dispatch for high-scoring candidates with:
  - threshold/cutoff controls,
  - deduplication window,
  - cooldown per asset,
  - optional severity bands by score quantile.
- System shall track alert counters and delivery outcomes.

### HM-5 Feature Store and Rolling Snapshot Retention

- System shall persist raw/derived feature rows and rolling snapshots for replay and calibration.
- System shall expose store health metrics:
  - feature row count,
  - rolling snapshot count,
  - storage size.
- System shall enforce retention/compaction policies to prevent unbounded growth.

### HM-6 Parameter Tuning and Governance

- System shall support parameter iteration with explicit versioned configs.
- System shall record parameter-set provenance for each emitted alert/signal.
- System shall require experiment validation before promoting parameter changes to live pathways.

### HM-7 Safety and Promotion Constraints

- Squeeze-monitor outputs shall remain advisory unless promoted through existing PQTS execution gates.
- Any automated execution derived from squeeze scores shall pass all Section 9 risk/execution controls and Section 10 regression checks.
- External performance claims without reproducible fills/PnL evidence shall be tagged `unverified`.

## 14. Additional Requirements from External Post (xmayeth, March 8, 2026)

These requirements are derived from the referenced “hold-to-resolution / hyperbolic discount” post and media.

### TD-1 Time-to-Resolution Value Model

- System shall support a time-discount-aware value model for event positions:
  - baseline form `V = A / (1 + k * D)`,
  - where `A` is remaining upside proxy, `D` is time-to-resolution, and `k` is configurable discount sensitivity.
- System shall allow per-market/per-category `k` calibration.

### TD-2 Hold-vs-Exit Policy Engine

- System shall evaluate each open event position with a hold policy that compares:
  - immediate realized gain if exited now,
  - expected remaining value if held to resolution,
  - risk-adjusted penalties (variance, liquidity, drawdown pressure, event risk).
- System shall default to hold-to-resolution when remaining expected value exceeds configurable opportunity-cost threshold.

### TD-3 Early-Exit Suppression Guard

- System shall include an early-exit suppression rule to prevent premature exits driven only by short-term mark-to-market gains.
- System shall permit early exit only when one or more gated conditions are met:
  - risk manager/kill switch action,
  - expected remaining value falls below threshold,
  - market integrity/liquidity degradation,
  - policy stop/time stop.

### TD-4 Resolution-Centric Lifecycle Tracking

- System shall classify closed positions with exit mode labels at minimum:
  - `held_to_resolution`,
  - `early_exit_policy`,
  - `risk_forced_exit`.
- System shall compute and store “foregone alpha” estimates for non-resolution exits.
- System shall expose hold-policy metrics:
  - hold rate,
  - average hold duration,
  - policy alpha vs manual/legacy baseline,
  - win rate segmented by exit mode.

### TD-5 Policy A/B and Promotion Rules

- System shall support A/B comparisons between hold-policy and baseline discretionary/legacy exit logic.
- Promotion of hold-policy logic shall require:
  - positive net alpha after costs,
  - no increase in unacceptable drawdown or risk-limit breach frequency,
  - successful completion of Section 10 regression matrix.

### TD-6 Advisory on External Performance Claims

- Claims such as “agent setup in 1 minute” or headline PnL improvements shall be treated as `unverified` unless backed by reproducible trade-level evidence.
- Only `observed` or validated `inferred` policy behaviors may be used as binding requirements.

## 15. Additional Requirements from External Post (zostaff, March 7, 2026)

These requirements are derived from the referenced post chain describing a 5-minute BTC HFT loop with an external analysis engine.

### ZQ-1 Split-Plane Architecture (Analysis vs Execution)

- System shall support separation between:
  - analysis plane (feature synthesis / signal scoring),
  - execution plane (low-latency order handling).
- System shall define a strict contract between planes (inputs, outputs, schema version, time budget).
- System shall fail closed (no order) when analysis payload is stale or malformed.

### ZQ-2 Short-Cycle Feature Evaluation Loop

- System shall support per-cycle scoring for short-cycle markets (default `5m` bucket).
- Minimum factor set in each scoring cycle shall include:
  - price vs target,
  - momentum,
  - volatility,
  - contract mispricing,
  - futures sentiment,
  - time decay.
- System shall log per-factor contributions for each emitted signal.

### ZQ-3 Latency and Throughput SLOs for HFT Path

- System shall expose execution latency SLOs for short-cycle strategy paths:
  - p95 and p99 submit-to-ack latency,
  - reject/timeout rate,
  - end-to-end decision-to-submit latency.
- System shall support configurable latency target budgets (including sub-50ms target profiles where venue/network permit).
- System shall auto-throttle or disable strategy path when latency or timeout SLOs are violated.

### ZQ-4 Kelly-Constrained Position Sizing

- System shall support Kelly-based sizing for short-cycle strategies with configurable fraction cap.
- Kelly output shall be bounded by existing hard risk limits (max order notional, leverage, participation, drawdown controls).
- System shall persist requested size vs risk-approved size for attribution.

### ZQ-5 High-Frequency Execution Governance

- System shall monitor trade-frequency metrics (trades/day, orders/minute, cancel/replace intensity).
- System shall enforce venue and internal rate-limit guards for high-frequency regimes.
- System shall support strategy-level guardrails for overtrading detection and cooldown.

### ZQ-6 Cross-Market Expansion Controls

- System shall support controlled expansion of a short-cycle strategy from BTC to additional assets (for example ETH/SOL) via explicit allowlist.
- Expansion shall require per-asset readiness checks:
  - liquidity/depth sufficiency,
  - slippage stability,
  - risk-capacity fit,
  - regression checks from Section 10.

### ZQ-7 Weather/Event-Market Exogenous Data Integration (Optional)

- System may support exogenous-data-backed event strategies (for example weather markets).
- Exogenous feeds shall include source quality metadata, timestamp freshness, and fallback behavior.
- Promotion of exogenous-data strategies shall require calibration and attribution evidence, not social-performance claims.

### ZQ-8 External Performance Claim Handling

- Headline claims (for example extreme percentage returns) shall be marked `unverified` unless reproducible with trade-level evidence.
- Requirements adopted from this post chain shall be limited to `observed` mechanics and validated `inferred` controls.

## 16. Additional Requirements from External Post (Marik, March 8, 2026)

These requirements are derived from the referenced Kyle-λ post and attached trading-media telemetry.

### KL-1 Kyle’s Lambda Market-Toxicity Estimation

- System shall estimate market-level Kyle’s lambda (`λ`) from observed aggressive order flow and subsequent price response:
  - `ΔP = λ * Q`.
- System shall update lambda estimates over rolling windows with configurable decay.
- System shall expose lambda confidence/quality metrics (sample size, fit error, update recency).

### KL-2 Adverse-Selection Guardrail

- System shall compare realized price impact against lambda-predicted impact for large aggressive flow events.
- System shall classify a market as `toxic_flow` when observed impact exceeds expected impact beyond configured threshold bands.
- System shall halt or sharply reduce strategy activity in `toxic_flow` markets until conditions normalize.

### KL-3 Impact-Aware Market Selection

- System shall include lambda-based filters in pre-trade market eligibility checks.
- System shall prioritize markets with lower impact-per-unit-flow when all other factors are comparable.
- System shall support per-market-type lambda thresholds (event markets vs short-cycle contracts).

### KL-4 Microstructure/Fair-Value Divergence Telemetry

- System shall track and log:
  - CLOB mid price,
  - model fair value,
  - divergence magnitude and direction,
  - convergence outcome after entry,
  - slippage/adverse fill events.
- System shall persist venue-comparison metadata when fair value references external sources.

### KL-5 Execution Diagnostics and SLO Coupling

- System shall correlate toxicity state with execution diagnostics:
  - latency,
  - fill quality,
  - reject/slip rate,
  - realized net alpha.
- System shall trigger strategy throttles when combined toxicity + execution degradation exceeds configured limits.

### KL-6 Risk and Promotion Constraints

- Lambda-based guards shall integrate with existing risk overlays and kill-switch decisions in Section 9.
- Any lambda-gated strategy promotion shall pass Section 10 regression checks and demonstrate out-of-sample benefit over non-lambda baseline.

### KL-7 External Claim Handling

- Public win-rate/PnL screenshots without reproducible order-level records shall be marked `unverified`.
- Binding requirements from this source shall remain limited to observable mechanics and validated inferred controls.

## 17. Additional Requirements from External Post (ZER, March 8, 2026)

These requirements are derived from the referenced post describing a whale-flow-triggered 15-minute BTC hedging loop.

### WF-1 Wallet-Flow Context Stream

- System shall support a pluggable wallet-flow context feed for prediction-market addresses.
- System shall maintain configurable watchlists (for example top-N active wallets by recent impact/performance).
- System shall track ingestion freshness and end-to-end wallet-event latency.

### WF-2 Whale Quorum Trigger Logic

- System shall support quorum-based triggers on coordinated wallet behavior:
  - minimum whale count,
  - max trigger window duration (for example 3+ wallets within 10 seconds),
  - same-side alignment requirement.
- System shall suppress duplicate triggers for the same market/interval during cooldown windows.

### WF-3 Pre-Move Entry and Immediate Hedge Workflow

- System shall support a two-step workflow:
  - directional entry on quorum trigger,
  - immediate opposite-side hedge under strict time budget.
- System shall enforce maximum allowed time between leg 1 and hedge leg 2.
- System shall enforce maximum unhedged exposure while hedge leg is pending.

### WF-4 Locked-Spread Validation

- System shall compute post-hedge locked payout math and reject cycles that do not meet minimum locked-margin thresholds after fees/slippage.
- System shall record cycle-level economics:
  - total leg cost,
  - theoretical payout,
  - locked margin,
  - realized slippage.

### WF-5 Latency and Reliability Gates for Whale-Flow Strategy

- System shall define per-strategy latency budgets for:
  - trigger detection,
  - entry submit/ack,
  - hedge completion.
- System shall auto-disable the strategy when latency budget breaches materially degrade lock quality or increase orphan-leg risk.

### WF-6 Safety and Scope Controls

- Whale-flow hedging strategy shall run only in explicitly allowed markets/intervals (default example: BTC 15m).
- Strategy shall remain subject to all existing PQTS controls in Sections 9-10 (profitability gate, capacity, confidence, shorting, kill switches, rate limits, idempotency).
- Strategy expansion to additional assets/intervals shall require readiness validation and regression verification.

### WF-7 External Claim Handling

- Social claims about returns or “zero risk” behavior shall be tagged `unverified` unless corroborated with reproducible cycle-level records.
- Binding requirements from this source shall be limited to observed mechanics and validated inferred controls.

## 18. Additional Requirements from External Post (Discover, March 8, 2026)

These requirements are derived from the referenced “article-vs-trader-behavior divergence” post chain.

### DV-1 Strategy-Knowledge Ingestion Pipeline

- System shall support ingestion of external strategy documents/articles into a structured research corpus.
- System shall extract normalized strategy claims from each document, including:
  - entry threshold claims,
  - volatility/risk guidance,
  - sizing guidance,
  - market-selection guidance.
- System shall store source provenance and extraction confidence per claim.

### DV-2 Author-to-Wallet Mapping Layer

- System shall support mapping published authors/entities to observable wallet identities where evidence exists.
- Mapping records shall include:
  - evidence source,
  - confidence score,
  - validity window,
  - conflict resolution rules.
- Low-confidence mappings shall not be used for live decisioning.

### DV-3 Publish-vs-Trade Divergence Detection

- System shall compare extracted published guidance against observed trade behavior for mapped wallets.
- System shall compute divergence metrics at minimum for:
  - mispricing entry thresholds (for example published 5% vs observed lower threshold),
  - volatility participation behavior,
  - position sizing/compounding behavior.
- System shall timestamp-align divergence analysis with publication times to detect post-publication behavior gaps.

### DV-4 Behavior-Weighted Strategy Overrides

- System may support behavior-weighted parameter overrides where observed wallet behavior systematically outperforms published guidance.
- Any override shall be bounded by existing risk and profitability controls.
- Overrides shall be versioned and reversible, with full audit trail.

### DV-5 Consensus Event Triggering

- System shall support consensus-style triggers when a configurable number of mapped wallets co-enter a market/position within a bounded time window.
- Consensus triggers shall include anti-noise controls:
  - minimum notional filter,
  - duplicate wallet-event suppression,
  - cooldown windows.

### DV-6 Research-to-Execution Governance

- Research-derived hypotheses (from article ingestion and divergence mining) shall execute through experiment stages before promotion:
  - offline validation,
  - paper campaign,
  - controlled canary.
- Promotion requires passing Section 10 regression checks and existing risk/promotion gates.

### DV-7 Source Reliability and Claim Handling

- Social PnL claims and copytrade promotional statements shall be labeled `unverified` unless backed by reproducible trade-level records.
- Requirements adopted from this source shall be restricted to observed mechanics and validated inferred controls.

## 19. Additional Requirements from External Post (Marlow, March 9, 2026)

These requirements are derived from the referenced post describing a low-price, high-multiple "penny sniper" approach and the links embedded in that post.

Observed outbound links:
- `https://t.co/BLrsonWdFT` (resolves to the same post's video/media page).
- `https://t.co/dV4s4m7olX` (resolves to `https://t.me/PolyGunSniperBot?start=ref_marlowxbt`).

### PS-1 Low-Price Candidate Scanner

- System shall support scanning a broad prediction-market universe (high-cardinality market set) for low-entry opportunities.
- System shall expose configurable candidate filters including:
  - `max_entry_cents` (default target from source context: 2-3 cents),
  - minimum projected payout multiple / target ROI threshold (default target from source context: ~1000%).
- System shall record which filter configuration produced each candidate decision.

### PS-2 Basket Campaign Construction

- System shall support campaign-style basket entry across many low-priced contracts rather than single concentrated bets.
- System shall enforce configurable micro-position sizing bounds (for example source-claimed $5-$25 per ticket), campaign budget caps, and maximum concurrent open tickets.
- System shall prevent duplicate exposure to the same market/outcome beyond configured limits.

### PS-3 Hit-Rate and Expectancy Guardrails

- System shall compute break-even hit-rate requirements from entry prices, fees, and slippage assumptions.
- System shall continuously compare realized hit-rate vs required break-even hit-rate over rolling windows.
- System shall auto-throttle or stop campaign expansion when realized expectancy degrades below configured limits.

### PS-4 High-Volume Settlement and Accounting

- System shall support high-ticket-count lifecycle handling:
  - open,
  - partial fill,
  - resolved win/loss,
  - payout reconciliation.
- System shall maintain auditable campaign-level PnL attribution, including winner concentration analysis (fraction of PnL from top-N hits).

### PS-5 External Wallet/Bot Signal Hygiene

- System may ingest externally observed wallet/account behavior as optional research or signal context.
- Any third-party bot/referral endpoint shall be treated as untrusted input and never granted wallet-signing authority by default.
- System shall support read-only shadow-follow mode before any live strategy coupling with external signal sources.

### PS-6 Throughput, Rate-Limit, and Latency Controls

- Scanner/execution loop for this strategy shall define explicit SLOs for:
  - market scan cycle time,
  - candidate-to-order latency,
  - orders-per-minute ceilings.
- Strategy shall respect venue/API rate limits and apply backoff and retry policies without violating Section 9 safety controls.

### PS-7 Source Reliability and Claim Handling

- Social claims (for example ROI, wallet PnL, follower counts, or anecdotal overnight gains) shall be labeled `unverified` unless reproducible from trade-level records and independent data capture.
- Requirements adopted from this source shall remain limited to observable mechanics and validated inferred controls.

## 20. Additional Requirements from External Post (Moon Dev, March 8, 2026)

These requirements are derived from the referenced post describing an AI-agent-driven trading-research loop and the outbound media link in that post.

Observed outbound links:
- `https://t.co/usX6Hqx3ms` (resolves to the same post's video/media page).

### RBI-1 Research-Backtest-Incubate (RBI) Pipeline

- System shall implement an explicit RBI lifecycle for strategy development:
  - Research (hypothesis generation and rule definition),
  - Backtest (historical validation with cost modeling),
  - Incubate (paper or constrained live canary).
- Strategy state transitions shall be versioned and auditable.

### RBI-2 Multi-Agent Role Separation

- System shall support role-specialized agent workers at minimum for:
  - research/spec drafting,
  - implementation,
  - backtest execution,
  - defect-fix/refactor loop.
- System shall store artifacts from each role (prompt/config, code diffs, test/backtest outputs, review decisions).

### RBI-3 Parallel Experiment Orchestration

- System shall support running multiple strategy experiments concurrently with configurable concurrency caps (source context references 18+ parallel runs).
- Each experiment shall use isolated config, seed, and output paths to prevent cross-run contamination.
- Scheduler shall prioritize experiments by expected information gain and resource budget.

### RBI-4 Promotion Gate Before Incubation

- System shall define explicit promotion thresholds before incubation (for example minimum return/risk criteria from source context).
- Promotion decisions shall require:
  - transaction-cost-aware backtest metrics,
  - robustness checks across parameter perturbations,
  - minimum sample-size constraints.
- Strategies failing thresholds shall be auto-rejected or sent back to research stage.

### RBI-5 Feature/Filter Ablation Requirements

- Backtest pipeline shall support ablation tests for key filters (for example volume filter present vs absent).
- System shall block promotion when a strategy's edge collapses under basic ablation or when filter dependence is unstable.

### RBI-6 Model Routing, Cost, and Reasoning-Budget Controls

- System shall support model-tier routing by task complexity (for example deeper-reasoning model for hard debugging, lower-cost model for bulk iteration).
- System shall enforce per-run and per-campaign token/cost ceilings.
- System shall enforce max reasoning/latency budgets and surface "no output due to reasoning budget burn" as a first-class failure mode.

### RBI-7 Evaluation Data Breadth and Reproducibility

- Research/backtest execution shall support multi-source data ingestion with provenance tracking for each experiment dataset.
- Experiment replays shall be reproducible from stored code revision, config, dataset snapshot, and random seed.

### RBI-8 Source Reliability and Claim Handling

- Public claims about model superiority, strategy returns, or "market-breaking" capability shall be marked `unverified` unless backed by reproducible experiment records.
- Requirements adopted from this source shall remain limited to observable workflow mechanics and validated inferred controls.

## 21. Additional Requirements from External Post Chain (Dexter's Lab, March 8, 2026)

These requirements are derived from the referenced post and its quoted link chain describing wallet-based copy trading and consensus-follow workflows.

Observed outbound links:
- `https://t.co/044XzTIyUn` (resolves to `https://twitter.com/DextersSolab/status/2026360538100387887`).
- `https://t.co/8NiTjdGflg` (resolves to same post image/media page).
- Quoted-chain link: `https://t.co/oe8efZKCAg` (resolves to `https://x.com/i/article/2026354868483436544`).
- Quoted-chain link: `https://t.co/M7mPZXIJgP` (resolves to `https://polymarket.com/@xdd07070?via=dexter-molu`).

### CT-1 Consensus-Over-Single-Wallet Decisioning

- System shall not rely on blind single-wallet mirroring as a default strategy mode.
- System shall support consensus-triggered entries across a wallet cohort in the same niche.
- Consensus policy shall be configurable for:
  - minimum tracked wallets (for example 10+),
  - minimum side-alignment threshold (for example ~80% on one side),
  - max trigger window duration.

### CT-2 Wallet Selection and Qualification Filters

- System shall score candidate wallets using multi-factor qualification, including:
  - consistency window (for example minimum 2-3 months),
  - monthly trade-frequency band,
  - niche specialization concentration,
  - drawdown behavior.
- System shall support configurable inclusion filters for:
  - historical PnL bands,
  - current value/minimum activity,
  - minimum total position count,
  - minimum win-rate.

### CT-3 Wallet Exclusion Heuristics

- System shall flag and optionally exclude wallets with characteristics associated with low-copy reliability:
  - ultra-high win-rate spread farming profiles,
  - extremely short track records / one-event spikes,
  - hyper-illiquid market dependence,
  - behavior patterns consistent with account-splitting or non-transparent loss reporting.
- Exclusion decisions shall be auditable and reversible.

### CT-4 Copy Execution Modes and Controls

- System shall support copy-sizing modes at minimum:
  - fixed notional,
  - exact source notional,
  - percentage-of-source trade,
  - portfolio-relative sizing.
- System shall enforce per-task execution controls including:
  - max slippage bound,
  - odds-range constraints,
  - stop-loss per copied position/task,
  - buy/sell mirroring mode selection.

### CT-5 Ongoing Rotation and Drift Management

- System shall support daily wallet-health review workflows and automated drift detection.
- Drift detection shall include:
  - sudden position-size regime changes,
  - category/niche drift,
  - deterioration in risk-adjusted performance structure.
- System shall support rotation actions (pause/remove/replace wallets) with full audit logs.

### CT-6 Portfolio Risk Overlay for Copy Baskets

- System shall enforce per-wallet and basket-level drawdown limits.
- System shall support correlation-aware exposure controls to avoid over-concentration in the same narrative/event cluster.
- System shall support periodic rebalance scheduling for copy baskets.

### CT-7 Market Impact and Liquidity Protection

- System shall estimate expected copy-trade impact relative to market liquidity before order submission.
- System shall throttle or skip entries where projected impact suggests the system would become exit liquidity.
- System shall track realized slippage vs projected impact by wallet and market.

### CT-8 Source Reliability and Claim Handling

- Public claims about copy-trading returns, win rates, or "retire-from-copy-trading" outcomes shall be marked `unverified` unless supported by reproducible trade-level records.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated inferred controls.

## 22. Additional Requirements from External Post Chain (Phosphen, March 8, 2026)

These requirements are derived from the referenced post and its quoted-link chain focused on risk-calculation diagnostics (variance drag, Sharpe, and drawdown remeasurement).

Observed outbound links:
- `https://t.co/sQUH53EG9f` (resolves to `https://twitter.com/phosphenq/status/2030325671692496922`).
- `https://t.co/kv3YanxqBJ` (resolves to same post video/media page).
- Quoted-chain link: `https://t.co/Ynenggbrkh` (resolves to `https://x.com/i/article/2030287110243065856`).

### VR-1 Variance-Drag Measurement Engine

- System shall compute and expose variance drag at strategy and portfolio level.
- System shall report both arithmetic-style average-return views and compounded/geometric return outcomes over matching windows.
- System shall provide a configurable approximation diagnostic for variance drag using volatility terms (for example variance-related drag estimates).

### VR-2 Belief-vs-Actual Performance Reconciliation

- System shall support user-entered expected metrics (for example expected Sharpe, expected max drawdown) and compare them against realized values.
- Dashboard shall explicitly show discrepancy deltas (for example "believed vs actual") for:
  - annualized return,
  - annualized volatility,
  - Sharpe ratio,
  - max drawdown,
  - variance-drag contribution.

### VR-3 Drawdown and Path-Dependency Diagnostics

- System shall compute rolling wealth index, rolling peak, drawdown series, and maximum drawdown from trade/equity-return streams.
- System shall include path-dependency diagnostics that highlight non-intuitive outcomes (for example alternating large gains/losses leading to negative compounded return).
- System shall include per-asset and portfolio-level contribution views for drawdown and drag.

### VR-4 Risk Calculator Workflow and Latency Targets

- System shall provide a one-run risk-calculator workflow that recalculates the full portfolio risk/return profile from current data.
- Workflow shall target fast turnaround suitable for interactive use (source context indicates "minutes" class updates, not batch-day latency).
- System shall log input snapshot time, formula version, and output timestamp for auditability.

### VR-5 Reproducible Formula and Code Outputs

- System shall support export of runnable analysis artifacts (for example Python snippets/notebooks) for core calculations:
  - annualized return,
  - annualized volatility,
  - Sharpe,
  - wealth/peak/drawdown series,
  - max drawdown,
  - variance-drag estimate.
- Exported code shall include pinned assumptions (periodicity, risk-free handling, missing-data policy, transaction-cost inclusion).

### VR-6 Data Quality and Metric Integrity Controls

- System shall enforce metric input-quality checks (return frequency consistency, missing intervals, outlier flags, stale-price detection).
- System shall block or warn on metric outputs when data integrity constraints are violated.
- All risk metrics used for gating live strategies shall remain subject to Section 10 regression verification.

### VR-7 Source Reliability and Claim Handling

- Claims about "hidden quant formulas," Sharpe uplift, or recovered alpha shall be marked `unverified` unless backed by reproducible data and formula outputs.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated inferred controls.

## 23. Additional Requirements from External Post Chain (LCSeekers, March 8, 2026)

These requirements are derived from the referenced post and quoted-link chain describing formula-driven prediction-market automation and strategy archetypes.

Observed outbound links:
- `https://t.co/UYpVfAx2Bj` (resolves to `https://twitter.com/zerqfer/status/2030293712748618062`).
- `https://t.co/hgYDSjWT47` (resolves to same post video/media page).
- Quoted-chain link: `https://t.co/iHO9hmQvwv` (resolves to `https://twitter.com/zerqfer/status/2029958444329934929`).
- Quoted-chain link: `https://t.co/DyasxsWtlc` (resolves to same quoted post video/media page).
- Second-chain link: `https://t.co/YdKXiEIGCt` (resolves to `https://x.com/i/article/2029955618765742080`, which is environment-login-gated).

### QF-1 Composite Edge Signal

- System shall support a composite edge score that includes at minimum:
  - model vs market probability gap magnitude,
  - probability-change speed term,
  - liquidity/market-depth factor.
- System shall expose configurable weights and thresholds for each component and log final score decomposition per decision.

### QF-2 LMSR-Aware Market Modeling

- System shall support computing LMSR-implied probabilities for relevant markets and comparing them to internal posterior probabilities.
- System shall expose liquidity-parameter sensitivity diagnostics and track edge persistence under parameter perturbations.

### QF-3 Sequential Bayesian Update Loop

- System shall support sequential posterior updates as new evidence arrives (news, on-chain flow, sentiment, and other configured streams).
- Each posterior update shall record evidence provenance, timestamp, and resulting probability delta.
- System shall track evidence-to-decision latency as a first-class metric.

### QF-4 Explicit EV Entry Gate

- System shall compute entry EV using model probability and executable market price, net of estimated costs/slippage.
- System shall enforce configurable minimum EV thresholds before entry (source-context default example: `EV > 0.10`).
- Entries failing EV gate shall be rejected and logged with reason codes.

### QF-5 Fractional Kelly Sizing Policy

- System shall compute full Kelly fraction and apply configurable fractional scaling (source-context default example: quarter Kelly).
- System shall cap sizing under adverse regime flags and enforce per-market/per-strategy max-notional controls.
- Full-Kelly deployment in short-horizon/high-frequency markets shall require explicit override and risk approval.

### QF-6 Strategy Archetype Module Support

- System shall support modular strategy families including:
  - oracle-lag timing module,
  - parity/arbitrage module (`YES + NO` mispricing),
  - information/sentiment lead-lag module,
  - market-making liquidity module.
- Each module shall inherit existing global risk and regression controls in Sections 9-10 before promotion.

### QF-7 Publish-vs-Behavior Divergence Mining

- System shall support extracting claimed strategy rules from public posts/articles and comparing them to observed trade behavior.
- Divergence analysis shall be timestamp-aware and sample-size-aware (minimum trade-count thresholds before inference).
- Divergence-derived parameter overrides shall follow the governance process in Section 18 and remain reversible.

### QF-8 Live Ops Hub and Sandbox Requirements

- System shall provide a real-time operations view with at minimum:
  - live and cumulative PnL,
  - current open positions,
  - active strategy/module states,
  - signal/feed health status.
- System shall provide an isolated sandbox/paper environment for testing new strategies before live rollout.
- Promotion from sandbox to live shall require passing Section 10 checks.

### QF-9 Source Reliability and Claim Handling

- Public claims on daily PnL, extreme account growth, or "hidden edge" performance shall be marked `unverified` unless supported by reproducible trade-level and metric records.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated inferred controls.

## 24. Additional Requirements from External Post Chain (slash1sol, March 8, 2026)

These requirements are derived from the referenced post and quoted-link chain about "hyperbolic discount" prediction-market bot workflows and Claude skill packaging.

Observed outbound links:
- `https://t.co/cotpTPaEgq` (resolves to `https://twitter.com/noisyb0y1/status/2030688100574167201`).
- `https://t.co/J9W3JemtLW` (resolves to same post video/media page).
- `https://t.co/IU46i2Di62` (resolves to `https://polyalerthub.com/?via=slash1a486`).
- Quoted-chain link: `https://t.co/QXm2CC40lk` (resolves to `https://twitter.com/RoundtableSpace/status/2030595632998580328`).
- Quoted-chain link: `https://t.co/qBdvnha5aR` (resolves to same quoted post media page).
- Second-chain link: `https://t.co/jEuH95NGn3` (resolves to `https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf`).
- Second-chain link: `https://t.co/udwk64U4ST` (resolves to same second-chain post media page).

### HD-1 Hyperbolic Discount Valuation Path

- System shall support time-discounted valuation modules including hyperbolic discount forms for near-term event pricing.
- System shall allow side-by-side diagnostics between hyperbolic and baseline discount choices (for example exponential) and record decision rationale.
- Discount-model parameters shall be versioned and backtest-auditable.

### HD-2 Deterministic Pre-Trade Rule Gate

- System shall enforce deterministic pre-trade rule checks before execution.
- Rule gate shall include at minimum:
  - minimum edge threshold check,
  - Kelly/fractional-Kelly size cap check,
  - bankroll and max-exposure check,
  - VaR(95%) daily-limit check.
- Gate results shall be logged per order attempt with pass/fail reasons.

### HD-3 Multi-Stage Agent Workflow

- System shall support an explicit staged workflow:
  - market scan,
  - research/signal enrichment,
  - probability prediction/calibration,
  - risk validation,
  - execution,
  - post-trade learning loop.
- Each stage shall emit structured outputs and latency metrics to support pipeline-level debugging.

### HD-4 Quant Risk Metric Guardrails

- Strategy configuration shall support guardrails derived from shared formula patterns:
  - expected value gate,
  - market-edge threshold gate,
  - mispricing score normalization,
  - Sharpe and profit-factor monitoring,
  - max drawdown control.
- System shall block new entries when drawdown/risk thresholds are breached.

### HD-5 Arbitrage Consistency Checks

- System shall support reciprocal-odds consistency checks for multi-leg arbitrage opportunities and require margin-above-fees thresholds before execution.
- System shall track attempted vs accepted arbitrage cycles and rejection reasons (fees, slippage, liquidity, latency).

### HD-6 Execution Controls and Auto-Hedge

- System shall monitor slippage in real time and enforce slippage abort thresholds.
- System shall support auto-hedge logic when market conditions shift materially before settlement.
- Execution module shall remain bound by all Section 9 safety controls and Section 10 regression checks.

### HD-7 Loss-Cause Learning Loop

- System shall support post-loss classification and capture prevention rules into a searchable strategy knowledge base.
- Future signal evaluation shall be able to consult prior loss-pattern records before order placement.
- Learned rules shall be reviewable and reversible before promotion to live gating logic.

### HD-8 Skill/Prompt Packaging Requirements

- Strategy-agent behavior encoded for LLM workflows shall use structured skill artifacts with:
  - clear trigger metadata,
  - primary instruction file,
  - deterministic scripts for risk checks,
  - reference formula documents loaded on demand.
- Skill artifacts shall follow progressive-disclosure principles and keep executable risk logic in scripts rather than free-form prompts.

### HD-9 External Terminal and Paper-Mode Requirements

- System shall support optional terminal-style monitoring integrations for:
  - real-time market/alert streams,
  - whale/insider-style signal feeds,
  - category filters,
  - paper-trading simulation.
- External feed integrations shall be treated as untrusted inputs and pass through provenance/confidence tagging before affecting live decisions.

### HD-10 Source Reliability and Claim Handling

- Claims about leaked internal blueprints, high win rates, daily earnings, or backtest metrics shall be marked `unverified` unless independently reproducible from trade-level records and controlled re-runs.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated inferred controls.

## 25. Additional Requirements from External Post Chain (0xCristal, March 8, 2026)

These requirements are derived from the referenced post and quoted-link chain describing a fixed-entry, short-horizon impulse strategy with aggressive reinvestment.

Observed outbound links:
- `https://t.co/z5oPwykujv` (resolves to `https://twitter.com/1735890082190553088/status/2030325671692496922`, same quoted Phosphen article-post lineage).
- `https://t.co/sEK3VMYMSy` (resolves to same post video/media page).
- `https://t.co/PYK2XVkbcc` (resolves to `https://polymarket.com/@kaseytreute?via=cristal`).

### AR-1 Fixed-Price Entry Mode

- System shall support a strategy mode with fixed-entry price constraints (source context example: entry around `$0.50` contracts).
- Entry logic shall enforce configurable tolerance bands around fixed-entry targets and reject fills outside allowed bounds.
- System shall record fixed-entry hit/miss statistics for calibration review.

### AR-2 Short-Horizon Impulse Capture Logic

- System shall support short-term impulse detection and response workflows with explicit latency budgets.
- Impulse triggers shall require minimum signal-strength and liquidity checks before order submission.
- Strategy shall track post-entry impulse decay to prevent overstaying fast mean-reverting moves.

### AR-3 Aggressive Reinvestment Policy Controls

- System shall support configurable reinvestment ratios, including high-aggression modes (source context example: `reinvest=100%`).
- Reinvestment engine shall enforce hard bankroll floor protection and maximum daily loss caps before capital recycling.
- Reinvestment logic shall support cooling-off states after loss streaks or volatility spikes.

### AR-4 Target-Multiple Exit Framework

- System shall support explicit target-multiple objectives for campaign progression (source context example: `target_mult=2x` step logic).
- Exit logic shall include both take-profit and protective unwind rules when target progression fails.
- System shall store realized vs target-multiple paths for each campaign cycle.

### AR-5 Compounding Path and Ruin-Risk Analytics

- System shall compute projected and realized compounding paths under the configured reinvestment policy.
- System shall include risk-of-ruin and drawdown trajectory analytics for aggressive compounding modes.
- Strategy shall auto-throttle or suspend when ruin-risk or drawdown thresholds exceed configured limits.

### AR-6 Session State, Telemetry, and Control Surface

- Runtime control surface shall expose at minimum:
  - session state (`idle/running`),
  - active/open positions,
  - recent closed trades,
  - scan/skip counters,
  - cumulative and session PnL.
- Operator actions (`start`, `pause`, `reset`) shall be auditable with timestamps and actor/source metadata.

### AR-7 Profile/Wallet Context as Optional Signal

- System may ingest external profile or wallet-level performance context as optional metadata for research and benchmarking.
- External profile metrics shall not be treated as authoritative without independent data reconciliation.
- Any profile-derived signal used in live decisioning shall carry source/provenance tags and confidence bounds.

### AR-8 Source Reliability and Claim Handling

- Public claims about rapid account growth, high win rates, or deterministic doubling paths shall be marked `unverified` unless corroborated with reproducible order-level records.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated inferred controls.

## 26. Additional Requirements from External Post Chain (0xRicker, March 8, 2026)

These requirements are derived from the referenced post and attached formula/backtest images describing an XGBoost+LLM signal stack with strict pre-trade risk gating.

Observed outbound links:
- `https://t.co/HzlA0nAAwx` (resolves to `https://twitter.com/noisyb0y1/status/2030688100574167201`).
- `https://t.co/KAqQQn0u73` (resolves to same post image/media page).

### RK-1 Model Stack and Probability Calibration

- System shall support hybrid signal generation combining structured model outputs (for example gradient-boosted models) with LLM-derived signals.
- System shall include probability calibration monitoring (for example Brier-score tracking) and re-calibration workflows.
- Strategy promotion shall require calibrated probability quality across out-of-sample windows.

### RK-2 Explicit Edge Threshold Gate

- System shall enforce an explicit minimum model-vs-market edge threshold before entry (source-context example: `edge > 0.04`).
- Edge gate shall be evaluated net of estimated transaction costs and slippage.
- System shall log gate pass/fail outcomes and threshold values per candidate trade.

### RK-3 Risk Gate Sequence and Latency Budget

- Pre-trade validation shall execute in deterministic sequence:
  - signal quality check,
  - sizing check,
  - VaR check,
  - exposure check,
  - execute or reject,
  - decision logging.
- System shall define and monitor pipeline latency SLOs for the full gate sequence (source context suggests sub-second budgets).

### RK-4 Fractional Kelly and Bankroll Caps

- System shall compute Kelly-based sizing and apply fractional scaling (source-context examples include alpha-style fractional coefficients).
- System shall enforce max-bet caps tied to bankroll and strategy risk tier.
- System shall expose configuration to tune aggressiveness without disabling hard risk limits.

### RK-5 Hard Risk Limits

- System shall support configurable hard limits including at minimum:
  - VaR(95%) cutoff,
  - maximum exposure ratio vs bankroll,
  - maximum drawdown stop threshold.
- Breach of any hard limit shall block new orders and trigger explicit risk-state alerts.

### RK-6 Signal-Quality and Microstructure Filters

- System shall support signal-quality filters derived from model divergence and volatility normalization (for example z-scored mispricing).
- System shall support order-flow toxicity checks (for example VPIN-style metrics) to suppress entries in toxic conditions.
- Multi-leg arbitrage opportunities shall require reciprocal-odds consistency checks and minimum residual margin thresholds.

### RK-7 Backtest Scoreboard and Category Breakdown

- Backtest reporting shall include at minimum:
  - total return,
  - Sharpe,
  - max drawdown,
  - profit factor,
  - trade count,
  - category-level win-rate breakdowns.
- System shall store both aggregate and segment-level metrics for regression comparisons.

### RK-8 Simulated-vs-Live Performance Separation

- System shall clearly label simulated/backtest metrics separate from live trading performance.
- Promotion and risk decisions shall not treat simulation metrics as live proof without forward validation.
- Reporting surfaces shall include warnings against over-interpreting historical simulation accuracy.

### RK-9 Source Reliability and Claim Handling

- Public claims about daily earnings, win rates, or return multipliers from this source chain shall be marked `unverified` unless corroborated by reproducible order-level records and independent replay.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated inferred controls.

## 27. Additional Requirements from External Post Chain (0xPhantomDefi, March 8, 2026)

These requirements are derived from the referenced post and quoted-link chain describing a structural two-leg mispricing loop on short-horizon BTC markets.

Observed outbound links:
- `https://t.co/rPPV7e1bqN` (resolves to `https://polymarket.com/@0x0eA574F3204C5c9C0cdEad90392ea0990F4D17e4-1769515653156`).
- `https://t.co/tPJFloAIu2` (resolves to `https://t.me/PolyGunSniperBot?start=ref_simbaa0x`).
- `https://t.co/pgvJDZyhQl` (resolves to `https://twitter.com/0xPhantomDefi/status/2023385836893483328`).
- `https://t.co/GlJIfDPaRq` (resolves to same post video/media page).
- Quoted-chain link: `https://t.co/tEqC9w2LSG` (resolves to `https://x.com/i/article/1788199581282422784`, environment-login-gated).

### PH-1 Market Scope and Timing Window

- Strategy shall support explicit scope restriction to target contracts (source context: BTC Up/Down 5-minute markets, with optional 15-minute variants).
- Strategy shall support intra-contract execution windows (source context: first ~4 minutes) and enforce no-new-entry cutoff near expiry.
- System shall expose per-market-type enable/disable controls to prevent accidental expansion.

### PH-2 Dual-Leg Parity Entry Rule

- Strategy shall support simultaneous two-leg entries (`YES` and `NO`) when combined executable price falls below a configurable threshold (< `$1.00` net of fees/slippage).
- System shall compute net locked margin after costs before execution and reject cycles below minimum margin.
- System shall enforce minimum order-book depth on both legs to reduce orphan-leg risk.

### PH-3 Hold-to-Resolution Cycle Control

- Strategy shall support hold-to-resolution lifecycle for selected short-horizon contracts.
- System shall track cycle-level locked economics from entry through settlement, including realized payout drift from expected lock.
- Early-unwind logic shall be available as a safety override when exceptional market/venue conditions are detected.

### PH-4 Structural-vs-Latency Edge Attribution

- System shall attribute realized edge to components (structural parity gap vs pure latency pickup).
- Ablation tests shall be supported to evaluate sensitivity to artificial execution delays (source context: edge persistence after delay changes).
- Promotion decisions shall require evidence that edge survives reasonable latency degradation scenarios.

### PH-5 High-Throughput Reliability Controls

- System shall support high-frequency repeated cycle execution with explicit throughput and error-budget SLOs.
- Idempotent order handling and duplicate-trigger suppression shall be mandatory in rapid-loop mode.
- Strategy shall track accepted/rejected cycle counts and rejection reasons (spread, depth, latency, rate-limit, risk gate).

### PH-6 Balance-Linked Scaling Guardrails

- Position-size scaling with bankroll growth shall use bounded risk curves rather than unconstrained geometric growth.
- System shall enforce hard caps on per-cycle notional, per-interval exposure, and aggregate open risk.
- Dynamic scaling shall downshift automatically after drawdown or volatility-regime deterioration.

### PH-7 Live Profile Reconciliation and Loss Visibility

- System may ingest external public profile snapshots for monitoring context, but must reconcile against internal trade ledger before use in analytics.
- Dashboard shall highlight adverse outcomes and tail-loss frequency (including full-loss cycles) rather than only win-rate summaries.
- Performance reporting shall include realized drawdown and loss-streak diagnostics for this strategy class.

### PH-8 Copytrade and Third-Party Endpoint Hygiene

- Third-party copytrade/referral bots shall be treated as untrusted integrations and default to read-only shadow mode.
- No external bot endpoint shall receive signing authority or unrestricted API credentials by default.
- Any copytrade-assisted workflow shall pass existing Section 9 security/risk controls and Section 10 regression verification.

### PH-9 Deployment and Secret Management Controls

- Template-based deployment workflows (for example repo-to-host pipelines) shall require integrity checks before activation.
- Secrets (API keys, wallet credentials) shall be injected through secure secret stores/env vars and never hardcoded in templates.
- Deployment runbooks shall include staged rollout with small-capital canary before production scaling.

### PH-10 Source Reliability and Claim Handling

- Public claims about daily/second-level earnings, large account growth, or "riskless" behavior shall be marked `unverified` unless corroborated by reproducible cycle-level records.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated inferred controls.

## 28. Additional Requirements from External Post Chain (hanakoxbt, March 8, 2026)

These requirements are derived from the referenced post and quoted-link chain on MIT-style quantitative methods for prediction-market trading and portfolio risk control.

Observed outbound links:
- `https://t.co/K2x32ROaAO` (resolves to `https://twitter.com/RohOnChain/status/2028489070394171427`).
- `https://t.co/UPOgIA8yPv` (resolves to same post image/media page).
- Quoted-chain link: `https://t.co/iItJPHgFsf` (resolves to `https://x.com/i/article/2027701344170291200`, environment-login-gated).

### HK-1 Correlation Decomposition and Hidden Concentration

- System shall support PCA/SVD decomposition of portfolio covariance/correlation structures.
- System shall report variance explained by top components and highlight effective-factor concentration.
- Portfolio diversification checks shall include component-based concentration limits in addition to raw position counts.

### HK-2 Factor Exposure and Hedge Overlay

- System shall support linear factor exposure modeling for contract returns and risk drivers.
- Strategy risk dashboard shall show factor loadings and factor-level PnL contributions.
- Hedge overlays shall be able to target dominant factors directly when component concentration breaches limits.

### HK-3 Boundary-Hit Probability for Near-Resolution Sizing

- System shall support boundary-crossing probability models (including gambler’s-ruin-style formulations) for short-horizon binary contracts.
- Position sizing near resolution shall incorporate boundary-hit probability and stop/target geometry, not only nominal edge.
- System shall surface expected stop-first probability under current boundary configuration before order confirmation.

### HK-4 Horizon-Scaling of Uncertainty

- Risk model shall scale uncertainty with time-horizon-aware rules (for example square-root-of-time baseline with documented assumptions).
- Multi-horizon markets (for example 5m vs 15m vs longer) shall use distinct volatility/risk parameter sets and not share a single static spread rule.

### HK-5 Volatility Clustering and Shock-Decay Modeling

- System shall support ARCH/GARCH-family volatility models to estimate post-shock variance decay.
- Quote-width and risk limits shall adapt to modeled shock persistence parameters.
- Spread normalization timing after information shocks shall be parameter-driven and auditable.

### HK-6 Heteroscedastic Regression and Robust Estimation

- Predictive modeling shall support heteroscedasticity-aware estimation (for example weighted/GLS-style variants) across contract lifecycle stages.
- Robust regression options shall be available for outlier-prone datasets (for example contested resolutions/oracle anomalies).
- Model training reports shall include diagnostics for residual variance stability and outlier influence.

### HK-7 VaR Ensemble and Assumption Divergence Alerts

- Risk engine shall support multiple VaR methods:
  - parametric,
  - historical simulation,
  - Monte Carlo.
- System shall alert when VaR method outputs diverge beyond configured tolerances, treating divergence as assumption-break risk.
- Risk approvals for high-notional campaigns shall require VaR ensemble review, not single-method output.

### HK-8 Martingale/Markov Assumption Boundaries

- Strategy documentation and validation shall explicitly separate:
  - fair-game baseline assumptions (martingale-style no-timing edge),
  - non-Markov microstructure features used for edge (if any).
- Any edge claim based on timing alone without probability advantage shall be treated as invalid in promotion review.

### HK-9 Data-Driven Education/Research Ingestion Governance

- System may ingest external educational/research content (for example open course notes) into the research corpus, but extracted rules shall pass staged validation before live use.
- Research-derived rules shall be tagged with source provenance, extraction confidence, and last-review timestamp.

### HK-10 Source Reliability and Claim Handling

- Public claims about proprietary quant advantage, portfolio-hedging certainty, or superior returns from educational material shall be marked `unverified` unless validated with reproducible trade-level evidence.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated inferred controls.

## 29. Additional Requirements from External Post Chain (ArchiveExplorer, March 8, 2026)

These requirements are derived from the referenced post and quoted-link chain describing weather-market automation patterns that rely on payoff asymmetry, model-consensus entries, and forecast-update latency.

Observed outbound links:
- `https://t.co/RYRCzthpLf` (resolves to `https://twitter.com/ArchiveExplorer/status/2030356343995924898`).
- `https://t.co/bxAOmK6UjI` (resolves to same post photo/media page).
- Quoted-chain link: `https://t.co/vbMSLXarRn` (resolves to same quoted post video/media page).
- Bot/referral link observed in this post chain: `https://t.me/KreoPolyBot?start=ref-flkooorr`.

### AX-1 Expectancy-First Strategy Evaluation

- System shall treat expectancy metrics as first-class promotion criteria, including at minimum:
  - average win,
  - average loss,
  - payoff ratio,
  - profit factor,
  - expected value per trade.
- System shall not allow win-rate-only gating for strategy promotion.
- Risk dashboard shall explicitly surface low-win/high-payoff profiles and low-payoff/high-win profiles as distinct regimes.

### AX-2 Payoff Asymmetry Guardrails

- Strategy configs shall support minimum required payoff asymmetry thresholds (win/loss multiple) before live activation.
- Position templates shall enforce bounded-loss definitions at order time and reject entries without explicit downside limits.
- Weekly performance review shall compare realized win/loss asymmetry against modeled assumptions and flag drift.

### AX-3 Multi-Model Weather Consensus Gate

- Signal generation shall support forecast consensus checks across multiple models (source context: GFS, ECMWF, ICON).
- Consensus gate shall be parameterized by maximum inter-model spread (source-context example: `< 2C`).
- Market/city mapping shall support per-location threshold overrides and model-health fallbacks.

### AX-4 Forecast-Update Clock Scheduling

- System shall support event-driven trading schedules aligned to upstream model release clocks (source context: GFS `00/06/12/18 UTC`, ECMWF `00/12 UTC`).
- Pre-update and post-update forecast snapshots shall be archived to enable deterministic delta computation.
- Time synchronization checks (NTP/clock-drift thresholds) shall be required for strategies dependent on release-time latency.

### AX-5 Stale-Price Capture and Pre-Settlement Exit Rules

- System shall compute stale-price opportunity scores by comparing fresh forecast deltas against current market quotes.
- Entry shall require configurable minimum stale-edge margin net of fees/slippage.
- Latency-capture mode shall support pre-settlement exit targets and maximum hold-time cutoffs (source-context example includes early exit near `$0.60+`).

### AX-6 Regime-Aware Swing Strategy Gating

- Mean-reversion/swing modules shall require measurable flip-frequency or volatility regime thresholds before activation.
- Strategy shall auto-throttle or disable when regime opportunity density falls below configured minimums.
- Regime classification metrics shall be logged and included in post-trade attribution for underperformance diagnosis.

### AX-7 High-Frequency Micro-Bet Controls

- System shall support micro-notional repeated execution patterns while enforcing per-market and per-interval notional caps.
- Rate limits shall be enforced across exchange API usage, data APIs, and alerting channels to prevent burst-induced failures.
- Execution telemetry shall track candidate count, accepted/rejected trades, and rejection reasons (spread/depth/latency/risk).

### AX-8 Data Feed Provenance and Resolution Integrity

- Weather inputs from multiple providers (for example Open-Meteo, NOAA, METAR-oriented feeds) shall be tagged with source, timestamp, and model version.
- Signal engine shall reject stale or conflicting inputs beyond configured tolerance bands.
- Settlement-sensitive strategies shall preserve auditable raw snapshots used for each trade decision.

### AX-9 External Bot and Copytrade Endpoint Hygiene

- Third-party bot/referral integrations (for example Telegram copy-assist endpoints) shall be treated as untrusted by default.
- No external bot endpoint shall receive withdrawal authority, private keys, or unrestricted trading credentials.
- Copy-assisted workflows shall run in shadow mode until they pass internal replay and risk-control conformance checks.

### AX-10 Source Reliability and Claim Handling

- Public claims about very high PnL with low win rate, large short-horizon compounding, or near-frictionless execution shall be marked `unverified` unless validated by reproducible trade-level ledgers.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated inferred controls.

## 30. Additional Requirements from External Post Chain (w1nklerr, March 8, 2026)

These requirements are derived from the referenced post and linked chain describing short-horizon crypto prediction-market automation using latency-sensitive execution, probability-vs-price mispricing, and micro-trade accumulation.

Observed outbound links:
- `https://t.co/7cqK7Nww8Y` (resolves to `https://t.me/PolyCop_BOT?start=ref_w1nklerr`).
- `https://t.co/YtCDdleQuz` (resolves to `https://polymarket.com/@PBot1?via=w1nklerr`).
- `https://t.co/VDVnH8qigk` (resolves to `https://twitter.com/w1nklerr/status/2018453276279070952`).
- `https://t.co/h7LCRKRgBf` (resolves to same post video/media page).
- Quoted-chain link: `https://t.co/NBd1QhtILj` (resolves to `https://x.com/i/article/2018378210413613057`, environment-login-gated).
- Related accessible article URL: `https://x.com/w1nklerr/article/2018453276279070952`.

### WK-1 Market Scope and Horizon Controls

- Strategy modules shall support explicit market scoping for short-horizon contracts (source context: BTC/ETH `5m` and `15m` up/down markets).
- System shall require per-horizon enable/disable controls and prohibit accidental expansion to unsupported market classes.
- Horizon-specific risk parameters shall be configurable and isolated.

### WK-2 Signal Families: Probability Gap and Parity Gap

- Entry logic shall support model-vs-market probability gap triggers (source-context threshold example: `> 0.3%`).
- Entry logic shall also support parity-gap triggers when executable `YES + NO < $1.00` net of fees/slippage.
- Each executed trade shall record which signal family (or combination) triggered entry.

### WK-3 Sequential Probability Update Engine

- System shall support sequential probability updates (Bayesian-style or equivalent online update formulation) for fast market re-pricing.
- Prediction state shall preserve prior, update input, and posterior snapshots for auditability.
- Update cadence shall be bounded by deterministic timing controls to avoid stale posterior use.

### WK-4 Latency SLO and Execution Pipeline

- Strategy runtime shall define and monitor end-to-end latency SLOs from signal detection to order placement (source context includes sub-second and `<100ms` goals).
- Async/event-driven architecture shall include explicit queue/backpressure controls for burst conditions.
- Breach of configured latency budgets shall trigger strategy throttling or temporary disablement.

### WK-5 Throughput Reliability and Order-Safety Controls

- High-frequency operation shall include idempotent order intents and duplicate-submit suppression.
- System shall enforce per-venue order-rate caps and reject-on-overrun safety behavior.
- Telemetry shall capture attempted order throughput, accepted/rejected counts, and rejection reasons.

### WK-6 Expected Value and Sizing Discipline

- Expected value computation shall be explicit (`estimated_probability - market_price`) and evaluated net of transaction costs.
- Position sizing shall support fractional Kelly or equivalent bounded sizing controls.
- Hard limits shall include per-trade bankroll cap and daily loss cap (source-context examples: `0.5%` per trade, `2%` daily stop).

### WK-7 Regime-Adaptive Risk Scaling

- Risk model shall classify market regime (for example sideways vs trending) and adapt sizing accordingly.
- Regime-based sizing adjustments shall remain within configured hard min/max risk bounds.
- Regime transition events shall be logged for post-trade attribution and diagnostics.

### WK-8 External Prediction Source Governance

- External prediction feeds (source context includes TradingView/CryptoQuant-style inputs) shall be versioned and timestamped on ingest.
- System shall validate source freshness, drift, and internal consistency before allowing trades.
- Conflicting or stale source states shall force no-trade outcomes until data quality recovers.

### WK-9 Public Profile Reconciliation and Tail-Loss Visibility

- Public wallet/profile metrics may be ingested as reference context only and shall not override internal trade ledger truth.
- System shall reconcile externally observed trade summaries with internal executions before performance attribution.
- Dashboard shall explicitly report tail-loss frequency, including full-loss outcomes, for high-frequency strategy classes.

### WK-10 Copytrade Endpoint Hygiene and Claim Handling

- Third-party copytrade bots/endpoints shall be treated as untrusted integrations by default and restricted to least-privilege access.
- External automation pathways shall remain in shadow mode until they pass internal replay, risk, and regression controls.
- Public claims about large profits, extreme throughput, or rapid setup time from this source chain shall be marked `unverified` unless validated with reproducible trade-level evidence.

## 31. Additional Requirements from External Post Chain (AleiahLock, March 8, 2026)

These requirements are derived from the referenced post and quoted-link chain describing LMSR mechanics, probability-coherent pricing, and liquidity-parameterized market-maker behavior.

Observed outbound links:
- `https://t.co/HnEE6ceC78` (resolves to `https://twitter.com/xmayeth/status/2029943091528950248`).
- `https://t.co/eNvW5dFXj1` (resolves to same post photo/media page).
- Quoted-chain link: `https://t.co/tVWtpLZsnH` (resolves to `https://twitter.com/xmayeth/status/2029943091528950248/photo/1`).
- Secondary quoted-chain artifact from linked post context: `https://t.co/NBd1QhtILj` (resolves to `https://x.com/i/article/2018378210413613057`, environment-login-gated).

### AL-1 LMSR Cost Function Fidelity

- System shall implement LMSR cost calculations for `N` outcomes using `C(q) = b * ln(sum_i exp(q_i / b))`.
- Implementation shall use numerically stable log-sum-exp computation to avoid overflow/underflow in high-inventory states.
- LMSR module shall support both binary and multi-outcome markets.

### AL-2 Marginal Price and Probability Coherence

- System shall compute LMSR-implied marginal prices as `p_i = exp(q_i / b) / sum_j exp(q_j / b)`.
- Price outputs shall be constrained to `[0, 1]` and satisfy `sum_i p_i = 1` within configured numerical tolerance.
- Any coherence violation beyond tolerance shall trigger explicit calculation-integrity alerts.

### AL-3 Liquidity Parameter (`b`) Governance

- Strategy configuration shall support per-market liquidity parameterization for LMSR sensitivity control.
- Changes to `b` shall be versioned, auditable, and restricted by risk-approval policy.
- Backtests and what-if analysis shall include slippage/impact comparisons across candidate `b` values.

### AL-4 Trade Impact and Delta-Cost Quoting

- Pre-trade quote engine shall compute delta cost (`C(q + delta) - C(q)`) for candidate order vectors.
- Execution preview shall include expected average fill price, post-trade implied probabilities, and projected impact.
- Orders exceeding configured impact/slippage bounds shall be rejected before placement.

### AL-5 Bounded-Loss and Subsidy Accounting

- Risk engine shall maintain LMSR bounded-loss accounting for market-maker-style simulations and overlays.
- Subsidy/risk budget consumption shall be tracked continuously against configurable maximum allowance.
- Breach of subsidy/risk budget shall disable affected LMSR-driven strategy pathways.

### AL-6 Inventory State Integrity

- System shall persist outcome inventory state (`q_i`) snapshots used for each pricing decision.
- State updates shall be atomic and idempotent to prevent race-condition pricing drift under concurrent execution.
- Replay tools shall be able to reconstruct implied probabilities from historical state snapshots.

### AL-7 LMSR-Based Mispricing Detection

- Signal layer shall support discrepancy detection between observed market quotes and LMSR-implied fair prices.
- Entry criteria shall require minimum discrepancy thresholds net of fees, spread, and execution risk.
- Signal attribution shall label discrepancy source class (for example inventory imbalance vs external-information shock).

### AL-8 Liquidity/Counterparty Independence Controls

- Strategy simulation shall support always-on-liquidity assumptions consistent with LMSR-style automated quoting.
- Live deployment shall include guardrails for venues where realized liquidity behavior deviates from LMSR assumptions.
- Liquidity-regime mismatch shall trigger no-trade or reduced-size behavior.

### AL-9 AI-Generated Strategy Artifact Governance

- Prompt-generated trading code/artifacts from external sources shall pass static analysis, dependency vetting, and sandbox replay before integration.
- Generated artifact provenance (prompt, model/version, generation timestamp, artifact hash) shall be retained for audit.
- No AI-generated strategy artifact shall be promoted to live execution without explicit regression and risk sign-off.

### AL-10 Source Reliability and Claim Handling

- Public claims about high annualized profits or rapid daily earnings from formula-only or prompt-only workflows shall be marked `unverified` unless validated by reproducible trade-level evidence.
- Requirements adopted from this source chain shall remain limited to observable LMSR mechanics and validated inferred controls.

## 32. Additional Delta Requirements from External Post Chain (noisyb0y1, March 8, 2026)

These requirements capture only net-new, trading-relevant deltas not already covered by prior sections (notably Sections 24 and 26), based on this post, its attached images, and quoted-link chain.

Observed outbound links:
- `https://t.co/QXm2CC40lk` (resolves to `https://twitter.com/RoundtableSpace/status/2030595632998580328`).
- `https://t.co/qBdvnha5aR` (resolves to same post photo/media page).
- Second-chain link: `https://t.co/jEuH95NGn3` (resolves to `https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf`).
- Second-chain link: `https://t.co/udwk64U4ST` (resolves to same quoted post media page).

### NS-1 Market-Universe Pre-Filter Gate

- Market scan stage shall include configurable pre-filters for at minimum:
  - liquidity floor,
  - volume floor,
  - bounded time-to-resolution window,
  - anomalous spread/move flags.
- Candidate markets failing any pre-filter shall not proceed to expensive research/model inference stages.

### NS-2 Ensemble-Confidence Fire Rule

- Multi-model signals shall require explicit confidence-threshold gating before order eligibility.
- Confidence gate shall be logged with component model confidence values and final aggregate confidence score.
- Low-confidence signal paths shall default to no-trade, not reduced-size speculative entries.

### NS-3 Independent Risk-Validator Quorum

- Pre-trade risk validation shall support independent validator paths (for example sizing, VaR, exposure, max-bet checks) executed in parallel.
- Any single validator failure shall veto execution.
- Validator outputs and veto reasons shall be persisted for replay and audit.

### NS-4 Parallel Sub-Agent Concurrency Controls

- System shall support per-market parallel sub-agent execution for signal generation with explicit concurrency caps.
- Concurrency settings shall include deduplication/collapse rules to prevent duplicate orders from simultaneous sub-agent agreement.
- Runtime telemetry shall report active sub-agent count, queue depth, and dropped/merged signal events.

### NS-5 Skill Trigger Precision Monitoring for Trading Agents

- LLM skill artifacts used for trading workflows shall define both positive and negative trigger scopes to reduce false activation.
- Runtime monitoring shall track under-trigger and over-trigger rates for each trading skill.
- Material trigger-quality degradation shall require version update and re-validation before continued live use.

### NS-6 Source Reliability and Claim Handling

- Public claims about daily earnings, fixed win rates, or productivity gains from external "cheat sheets" shall be marked `unverified` unless validated with reproducible trade-level evidence and controlled re-runs.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated inferred controls.

## 33. Additional Delta Requirements from External Post Chain (0xPhilanthrop, March 8, 2026)

These requirements capture net-new, applicable deltas from this weather-bot post chain and linked setup article, without duplicating prior weather strategy sections.

Observed outbound links:
- `https://t.co/X1782nE0So` (resolves to `https://twitter.com/0xPhilanthrop/status/2025648591553855933`).
- `https://t.co/hXUSMkYkKT` (resolves to same post video/media page).
- `https://t.co/UlvSrUzZGN` (resolves to `https://t.me/KreoPolyBot?start=ref-53blg718p7`).
- Quoted-chain link: `https://t.co/3pPgTaQ6lH` (resolves to `https://x.com/i/article/2025634403129446400`, environment-login-gated).
- Related accessible article URL: `https://x.com/0xPhilanthrop/article/2025648591553855933`.

### PL-1 Weather Distribution-to-Bucket Probability Mapping

- Weather strategy shall convert forecast distributions (not only point forecasts) into per-bucket event probabilities for temperature/humidity bucket markets.
- Probability-mapping logic shall record source forecast timestamp, horizon, and uncertainty band used for each mapped bucket.
- Trades shall be blocked when forecast uncertainty bands are too wide to produce stable bucket-level edge estimates.

### PL-2 Paired Entry/Exit Threshold Profile Governance

- Weather modules shall support paired threshold profiles (entry threshold + exit threshold) as versioned configuration units.
- Threshold profiles shall enforce minimum separation between entry and exit levels to avoid churn trades.
- Profile changes shall require canary validation before broad rollout.

### PL-3 Per-Scan Trade Budget and Market Universe Controls

- System shall enforce per-scan trade-budget limits (for example max trades per scan cycle) in addition to per-trade sizing caps.
- Weather scanning shall support explicit city/market allowlists and deny-lists.
- Scan-cycle logs shall include scanned market count, eligible count, and executed count per cycle.

### PL-4 Segregated Execution Wallet and Funding Guardrails

- Strategy execution shall use a segregated agent wallet/account distinct from treasury holdings.
- System shall enforce funding caps for execution wallets and configurable auto-pause when funded capital exceeds policy limits.
- External claim/attach workflows for strategy agents shall require explicit operator approval and signed audit events.

### PL-5 Unattended Operation Watchdogs

- Long-running autonomous strategy mode shall require heartbeat monitoring for:
  - market data freshness,
  - forecast feed freshness,
  - execution gateway health.
- Missing heartbeats or repeated stale-feed detections shall trigger automatic safe-mode pause.
- Recovery from safe-mode shall require explicit health revalidation before resuming live orders.

### PL-6 Third-Party Skill/Module Supply-Chain Controls

- Third-party strategy modules installed from external hubs/marketplaces shall require version pinning and integrity verification before activation.
- Installed module metadata shall include source URI, version, hash/signature status, and granted permissions.
- Module upgrades shall default to manual approval and staged rollout.

### PL-7 Source Reliability and Claim Handling

- Public claims about weather-forecast accuracy translation into trading certainty, extreme ROI from small bankrolls, or passive unattended gains shall be marked `unverified` unless supported by reproducible trade-level evidence.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated inferred controls.

## 34. Additional Delta Requirements from Direct Bot Link (PolyGunSniperBot, March 9, 2026)

These requirements capture net-new, applicable deltas from the direct bot link and publicly accessible associated assets.

Observed outbound/associated links:
- `https://t.me/PolyGunSniperBot?start=ref_marlowxbt` (direct user-provided link).
- Public associated group page: `https://t.me/polygun` (references the same bot).
- Public associated site: `https://polygun.xyz`.

### PG-1 Wrapper-Fee-Aware Execution Gate

- Execution engine shall support endpoint-specific wrapper fee schedules on top of venue fees (source context includes a stated bot fee model).
- Net-edge checks shall evaluate entry/exit decisions using round-trip cost including both venue and wrapper-layer fees.
- Orders shall be rejected when expected net EV is non-positive after full fee stack and slippage assumptions.

### PG-2 Chat-Native Limit Order Lifecycle Controls

- Telegram/chat-driven trading integrations shall support full limit-order lifecycle controls:
  - create,
  - amend/replace,
  - cancel,
  - expiry/timeout.
- Limit-order workflows shall include duplicate-intent suppression and idempotent retries.
- Order-state transitions from chat integrations shall be fully auditable in the core execution ledger.

### PG-3 Bot-Generated Wallet Lifecycle and Recovery Controls

- If an integration generates execution wallets, system shall require export/recovery verification before enabling unattended trading.
- Wallet lifecycle events (generation, export, rotation, deactivation) shall be logged with operator attribution.
- Trading shall be blocked for wallets lacking verified recovery state or policy-compliant key handling.

### PG-4 Auto-Bridge Deposit Reconciliation

- Multi-chain deposit/auto-bridge flows shall require end-to-end reconciliation before funds are considered tradable.
- Reconciliation shall track:
  - source chain/asset,
  - bridge route,
  - fees/slippage,
  - destination settlement confirmations.
- Strategy execution shall remain paused on unresolved bridge-state ambiguity.

### PG-5 Copy-Mirroring Control Plane Hardening

- Copy-trading integrations shall expose explicit follower-side controls for per-leader sizing caps, market allowlists, and slippage bounds.
- Follower execution shall support immediate kill-switch detachment from leaders without closing unrelated positions.
- Mirror-lag metrics (leader action time vs follower execution time) shall be tracked and enforced against configured tolerances.

### PG-6 Promotional PnL Artifact Separation

- Shareable performance artifacts (for example bot-generated PnL cards) shall be clearly labeled as promotional summaries, not accounting truth.
- All promotional PnL outputs shall be derivable from the audited trade ledger with reproducible calculation paths.
- Any mismatch between promotional artifact values and ledger-derived values shall trigger compliance alerts.

### PG-7 Source Reliability and Claim Handling

- Public claims around "smart money" copy performance, partner counts, or turnkey bot profitability shall be marked `unverified` unless validated with reproducible trade-level evidence.
- Requirements adopted from this direct-link chain shall remain limited to observable mechanics and validated inferred controls.

## 35. Additional Delta Requirements from External Post Chain (hanakoxbt latency, March 8, 2026)

These requirements capture net-new, applicable deltas from this latency-arbitrage post chain without duplicating prior weather/copytrade/latency sections.

Observed outbound links:
- `https://t.co/tiqetBJOZV` (resolves to same post video/media page).
- `https://t.co/PTZuvewZE6` (resolves to `https://kreo.app/@1743116`).
- Resolved referral target from linked page: `tg://resolve?domain=KreoMainBot&start=ref-1743116` (via public landing content).

### HL-1 Latency-Normalized Opportunity Scoring

- Latency-arbitrage signal ranking shall support a latency-normalized score using expected edge contribution and measured latency gap.
- Score computation shall be numerically stable and include denominator floors to avoid divide-by-near-zero amplification.
- Opportunity scoring inputs shall be logged per trade candidate for replay and attribution.

### HL-2 Micro-Window Execution Integrity

- Strategy runtime shall support sub-second execution windows with explicit micro-window freshness limits for candidate opportunities.
- Opportunities older than configured freshness thresholds at order-send time shall be dropped.
- Execution telemetry shall capture per-leg timing:
  - data ingest timestamp,
  - decision timestamp,
  - order submit timestamp,
  - venue acknowledgement timestamp.

### HL-3 Pre-Close Entry Gating

- Strategy shall support pre-close entry windows for rapidly converging spreads with configurable safety margins.
- Pre-close entry logic shall require synchronized clocks and enforce max jitter/skew tolerances.
- If clock/jitter checks fail, pre-close mode shall auto-disable until health recovers.

### HL-4 Convergence-Exit Automation

- Latency-arbitrage positions shall support automatic convergence-based exit rules with explicit target conditions.
- Exit logic shall include max-hold fail-safe and adverse-move abort thresholds.
- System shall record realized convergence quality vs expected convergence assumptions.

### HL-5 Feed Lead-Lag Provenance and Entitlement Controls

- External real-time feeds used for lead-lag strategies shall be tagged with provenance, receipt-time, and entitlement/license metadata.
- Strategy shall reject signals from feeds that fail entitlement, freshness, or integrity checks.
- Any strategy pathway that could rely on private/non-public feed access shall remain blocked per policy.

### HL-6 Latency-Edge Capacity and Decay Monitoring

- System shall track realized edge as a function of observed latency bucket (for example by 10ms bins) to detect edge decay.
- Capacity expansion decisions shall require evidence that edge persists at higher throughput and under realistic queueing delays.
- Latency-edge decay breaches shall trigger automatic size downshift or strategy pause.

### HL-7 Source Reliability and Claim Handling

- Public claims about sub-second certainty, very high Sharpe/win-rate, or rapid bankroll growth from latency edge shall be marked `unverified` unless validated with reproducible trade-level records.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated inferred controls.

## 36. Additional Delta Requirements from External Post Chain (dreyk0o0, March 8, 2026)

These requirements capture net-new deltas from this post chain, while treating factor/PCA/GARCH content as already covered by prior sections.

Observed outbound links:
- `https://t.co/HwVlvBHZU3` (resolves to `https://twitter.com/RohOnChain/status/2028489070394171427`).
- `https://t.co/SG9npZjK1a` (resolves to same post video/media page).
- Linked referral in post body: `https://t.co/PTZuvewZE6` (resolves to `https://kreo.app/@1743116` -> `KreoMainBot` landing target).

### DK-1 Causal Time-Alignment and Lookahead Prevention

- Any lead-lag strategy using external event feeds and market quotes shall enforce causal as-of alignment at decision time.
- Signal computation shall be blocked when feed timestamps or market snapshots cannot prove causal ordering.
- Backtests and replays shall include explicit anti-lookahead validation and fail on time-order violations.

### DK-2 Event-Feed Revision and Finality Handling

- Strategies using sports/political outcome-count feeds shall model event states as provisional vs final.
- Trade logic shall define behavior for feed revisions (for example reprice, reduce, or flatten) when prior event data is corrected.
- Audit logs shall preserve original and revised feed payloads with revision timestamps.

### DK-3 Cross-Domain Latency Baselines and Drift Alerts

- Latency-arbitrage models shall maintain separate latency baselines by feed domain (for example sports vs politics) and by venue pathway.
- System shall alert and down-weight/disable signal paths when observed latency gap drifts below edge-viable thresholds for that domain.
- Capacity and sizing policy shall reference domain-specific latency distributions rather than global averages.

### DK-4 Source Reliability and Claim Handling

- Public claims about high Sharpe, high win-rate, or rapid capital growth from latency advantage shall be marked `unverified` unless supported by reproducible trade-level evidence.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated inferred controls.

## 37. Additional Delta Requirements from External Post Chain (0xwhrrari, March 8, 2026)

These requirements capture net-new, applicable deltas from this post chain focused on two-sided liquidity provisioning and reward-based return decomposition.

Observed outbound links:
- `https://t.co/NARQL8CgJn` (resolves to same post video/media page).

### WR-1 Two-Sided Liquidity Provisioning Mode

- Strategy layer shall support a non-directional two-sided quoting mode that places both `YES` and `NO` liquidity on the same market.
- Two-sided mode shall include inventory-neutrality targets and configurable max skew tolerance between legs.
- Strategy shall block activation when depth/liquidity conditions cannot support safe two-sided operation.

### WR-2 Fill-State Outcome Engine

- Execution lifecycle shall model distinct fill states for two-sided liquidity mode:
  - no-fill reward accrual state,
  - one-leg-fill with hedge/rebalance state,
  - both-legs-filled neutral-close state.
- Each state transition shall define deterministic actions and risk checks.
- State-machine transitions and terminal outcomes shall be logged for replay.

### WR-3 Reward-Aware Net PnL Decomposition

- PnL analytics shall decompose returns into:
  - liquidity/reward income,
  - trade spread/convergence PnL,
  - fees/slippage costs.
- Strategy gating shall evaluate expected net return after reward uncertainty and execution costs.
- Reward accrual claims shall be reconciled against verifiable venue/account records.

### WR-4 One-Leg Fill Hedge Controls

- When only one side fills, system shall support immediate hedge logic with strict latency bounds and max-loss controls.
- Hedge logic shall enforce configurable combined-price and cost ceilings before completion (source context includes combined-leg profitability framing).
- Failed hedge completion within time/cost bounds shall trigger emergency risk mitigation (size reduction or flatten).

### WR-5 Niche-Market Competition Scoring

- Market selection for liquidity-reward strategies shall include competition-density scoring (for example participant count/depth concentration proxies).
- Strategy shall rank candidate markets by expected reward-share efficiency net of fill risk.
- Capacity expansion into mainstream/high-competition markets shall require separate approval thresholds.

### WR-6 Source Reliability and Claim Handling

- Public claims about deterministic reward farming, first-night earnings, or "no luck involved" outcomes shall be marked `unverified` unless validated with reproducible trade-level and reward-ledger evidence.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated inferred controls.

## 38. Additional Delta Requirements from External Post Chain (DenisKursakov, March 8, 2026)

These requirements capture net-new, applicable deltas from this post chain and its referenced copy-trading terminal context.

Observed outbound links:
- `https://t.co/S5L6bzTZT2` (resolves to `https://twitter.com/zodchiii/status/2030267008625873324`).
- `https://t.co/dajOVwXm7o` (resolves to same post video/media page).
- Mentioned copy endpoint in post text: `@prob_trade` (profile context references `https://prob.trade/`).
- Quoted-chain link from linked post: `https://t.co/kx4hKgCVSE` (resolves to `https://x.com/i/article/2030259380055126016`, environment-login-gated).

### DN-1 Social Wallet Address Ingestion and Validation

- Research ingestion shall support extracting published on-chain wallet addresses from external posts.
- Extracted addresses shall pass chain-format validation and checksum normalization before being used in analytics.
- Address-to-entity mappings shall include source evidence, confidence level, and conflict-handling rules.

### DN-2 Directed Market-List Trading Mode

- System shall support a directed execution mode where users provide explicit candidate market lists (for example JSON/CSV import).
- Directed mode shall enforce schema validation, deduplication, and market-status checks before any order routing.
- When directed mode is active, autonomous discovery outside the provided universe shall remain disabled by default.

### DN-3 Preference-Constrained Adaptive Tuning

- Any preference-learning loop from user-directed runs shall be bounded by configured parameter guardrails.
- Learned parameter updates shall be versioned, auditable, and reversible.
- Promotion of learned adjustments to autonomous mode shall require canary validation.

### DN-4 High-Probability Tail-Risk Overlay

- Strategies targeting very high implied-probability markets (for example 95-99% ranges) shall include explicit tail-risk hedge overlays.
- Tail-risk controls shall include scenario tests for low-frequency/high-impact reversals ("black swan"-class events).
- Per-strategy hard loss caps shall apply even when baseline model confidence is high.

### DN-5 Source Reliability and Claim Handling

- Public claims about extreme account growth from copied weather-wallet behavior shall be marked `unverified` unless supported by reproducible trade-level records.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated inferred controls.

## 39. Additional Delta Requirements from External Post Chain (Shelpid_WI3M follow-up, March 8, 2026)

These requirements capture net-new deltas from this post chain, especially around confidence-driven order splitting behavior in ultra-short crypto horizons.

Observed outbound links:
- `https://t.co/S5L6bzTZT2` (resolves to `https://twitter.com/zodchiii/status/2030267008625873324`).
- `https://t.co/dajOVwXm7o` (resolves to same post video/media page).
- Mentioned profile link in post body: `https://polymarket.com/@gabagool22?via=shelpid`.
- Mentioned copytrade link in post body: `https://t.me/KreoPolyBot?start=ref-shelpid`.

### SH-1 Confidence-Ladder Order Slicing

- Short-horizon execution shall support splitting each trade intent into multiple child entries with fixed clip-size bounds.
- Size escalation across child entries shall be monotonic and only allowed when confidence increases under the same market state.
- If confidence weakens mid-sequence, remaining child entries shall be canceled by default.

### SH-2 Child-Order Sequence Integrity

- Child-order sequences shall enforce maximum sequence duration and stale-signal cutoffs.
- Sequence controller shall prevent overlapping sequences for the same market/side unless explicitly permitted by policy.
- Every child fill/cancel/reject event shall be linked to its parent signal for replay and attribution.

### SH-3 Ultra-Short Horizon Regime Isolation

- Strategy configs for 5-minute and 15-minute market classes shall use isolated parameter sets (entry/exit, sizing, latency, risk limits).
- Cross-horizon parameter bleed-over shall be disallowed unless explicitly version-approved.
- Regression tests shall validate that a change in one horizon profile does not alter another profile's behavior.

### SH-4 High-Volume Micro-Execution Reliability Budget

- High-frequency probability-farming paths shall define error budgets normalized by execution count (for example failures per 1,000 orders).
- Breach of normalized error budgets shall trigger automatic downshift in execution rate and order-sequence depth.
- Dashboards shall expose throughput, reject causes, and realized edge per execution bucket.

### SH-5 Source Reliability and Claim Handling

- Public claims about very large profit totals, monthly income, or high win-rate from this source chain shall be marked `unverified` unless validated with reproducible trade-level records.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated inferred controls.

## 40. Additional Delta Requirements from Reddit Post + Linked App (PolyMRR, March 9, 2026)

These requirements capture net-new, applicable deltas from the referenced Reddit post and linked app implementation, focused on metric-grounded market design and forecast-engagement loops.

Observed outbound links:
- `https://www.reddit.com/r/SideProject/comments/1rp3mhj/i_built_polymarket_for_startups/`
- `https://www.polymrr.com/`
- `https://www.polymrr.com/markets`
- `https://www.polymrr.com/leaderboard`
- `https://trustmrr.com/` (referenced as the upstream metric source in linked app data)

### RP-1 Deterministic Metric-Backed Resolution Contracts

- Each market shall store a machine-readable resolution contract including `metric`, `target`, `condition` (`gte`/`lte`/`eq`), source-field ID, and close timestamp.
- Human-readable resolution text shall be generated from the contract and remain semantically consistent with it.
- Any resolution-contract mutation after first fill shall require a version bump, halt, and explicit migration policy.

### RP-2 Verified-Data Oracle and Snapshot Finality

- Settlement for metric-backed markets shall consume as-of snapshots from approved data providers with provider/version/timestamp provenance.
- Pre-close observation, close-time observation, and final settlement snapshot shall be archived for replay and dispute handling.
- Missing or late provider data shall move markets to `pending_resolution` instead of forcing settlement with stale values.

### RP-3 Startup/Founder Market Template Library

- System shall support template families for MRR upside targets (`mrr`, `gte`) with configurable thresholds.
- System shall support template families for downside threshold markets (`mrr`, `lte`) with configurable thresholds.
- System shall support template families for 30-day revenue milestones (`revenue_30d`, `gte`) with configurable thresholds.
- System shall support template families for acquisition/listing status (`on_sale`, `eq`) with deterministic boolean resolution.
- System shall support template families for founder social milestones (`x_follower_count`, `gte`) with deterministic source mapping.

### RP-4 Entity-Centric Market Graph

- Markets shall be linked to canonical startup/founder entities with stable IDs, aliases, and external handles.
- Entity views shall expose active/resolved markets and the core metrics used for settlement context.
- Duplicate entity records shall be merged via deterministic identity rules with conflict/audit logs.

### RP-5 Virtual-Credit Engagement Environment

- Paper engagement mode shall support non-custodial virtual credits with explicit `no real-money payout` labeling.
- New accounts shall receive a configurable starter balance and pass the same execution/risk controls used in paper mode.
- Virtual-mode performance shall not auto-promote to live capital without independent validation gates.

### RP-6 Market Discovery and Coverage Controls

- Discovery surfaces shall support filters across market status, market type, category, sort mode, and free-text search.
- Coverage dashboards shall expose counts for open markets, tracked entities, and participation activity.
- Minimum depth/participant thresholds shall be enforceable before a market is eligible for model training or live decisioning.

### RP-7 Public Activity Feed with Privacy-Safe Telemetry

- System shall provide a live activity feed containing market action side, notional, timestamp, and market ID.
- Feed pipeline shall enforce idempotency/deduplication so single actions cannot appear multiple times.
- Feed events shall remain replayable for behavior analysis and post-incident reconstruction.

### RP-8 Reputation Leaderboard Quality Controls

- Leaderboards shall rank participants using forecast-quality metrics (profit, win rate, and proper scoring where available) with minimum sample-size gates.
- Rankings shall separate unresolved-market exposure from resolved-market performance.
- System accounts (for example market-maker/liquidity accounts) shall be excluded from competitive user rankings by default.

### RP-9 Source Reliability and Claim Handling

- Claims from this source chain about traction, participant counts, or verified-revenue totals shall be marked `unverified` unless reproducible from captured datasets and audit logs.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated inferred controls.

## 41. Additional Productization + Distribution Requirements (Grok Synthesis, March 9, 2026)

These requirements capture net-new system capabilities focused on adoption, reproducibility, and external visibility.

Source context:
- User-provided Grok synthesis (March 9, 2026) covering PQTS growth gaps vs public quant OSS competitors.

### GK-1 One-Command Container Runtime

- System shall provide a one-command containerized runtime using `docker-compose` with at least: core app runtime, Streamlit dashboard, Redis, and Postgres services.
- Container stack shall include deterministic local startup with health checks and documented environment variable mapping.
- Optional observability services (for example Grafana) shall be supported as opt-in profiles without blocking base startup.

### GK-2 Public Simulation Leaderboard Publication

- System shall support automated export of the latest simulation leaderboard artifact to a static web target.
- Publication pipeline shall ingest `data/reports/simulation_leaderboard_*.csv`, normalize schema, and render human-readable leaderboard output.
- Published leaderboard snapshots shall include generation timestamp and source commit reference for traceability.

### GK-3 Operator Notification Integrations (Telegram/Discord)

- System shall provide outbound notification integrations for Telegram and Discord.
- Notifications shall support at least trade alerts, daily PnL summary, and kill-switch/risk-halt events.
- Notification delivery shall enforce deduplication and rate limiting controls to prevent alert floods.

### GK-4 Historical Dataset Bootstrap and Seeding

- System shall provide deterministic historical data bootstrap tooling with exchange ingestion support and local cache persistence.
- Tooling shall support seeded sample datasets spanning configurable date windows (including 2024-2026 campaign windows).
- Seed pipeline shall produce reproducible manifests (symbols, intervals, date bounds, checksums) for experiment replay.

### GK-5 Hyperparameter + Purged-CV Automation

- System shall support automated hyperparameter search workflows with purged cross-validation appropriate for time-series leakage control.
- Search runs shall persist parameter sets, fold-level metrics, and selected winner rationale for auditability.
- Promotion from optimization output to deployable config shall require existing readiness/promotion gates.

### GK-6 Automated Monthly Performance Report Builder

- System shall generate scheduled monthly performance reports in machine-shareable and human-readable formats.
- Reports shall include at minimum equity curve outputs and risk/return tables (including Sharpe and drawdown metrics).
- Report jobs shall preserve source run IDs and config references for reproducibility.

### GK-7 Strategy Scaffolding and Plugin Extension Interface

- CLI shall support strategy scaffolding via a command equivalent to `pqts new-strategy`.
- New strategy templates shall include required contract hooks, registration stubs, and test skeletons.
- System shall support a plugin registration interface so externally contributed strategies can be loaded without modifying core package internals.

### GK-8 Hybrid Backtesting Execution Modes

- Backtesting subsystem shall support both vectorized fast mode and event-driven high-fidelity mode.
- Runtime shall expose explicit mode selection and document tradeoffs (speed vs microstructure accuracy).
- Regression parity checks shall compare key outcomes across modes and flag unacceptable divergence.

### GK-9 Prometheus-Compatible Metrics Surface

- Runtime shall expose a metrics endpoint compatible with Prometheus scraping.
- Metrics shall cover execution health, risk-state transitions, and strategy-level performance counters.
- System shall include importable Grafana dashboard templates aligned with exposed metric names.

## 42. Web App Architecture Requirements (March 9, 2026)

These requirements define the primary product web-stack direction for PQTS.

### WA-1 Primary Backend Framework

- Product-facing web APIs shall be implemented with Python `FastAPI` as the primary backend service framework.
- Backend shall expose typed OpenAPI contracts for all external HTTP endpoints.
- Backend shall support async request handling for low-latency market/status surfaces.

### WA-2 Primary Frontend Framework

- Product-facing web UI shall be implemented with `Next.js` and TypeScript.
- Frontend shall consume backend APIs via versioned REST and WebSocket interfaces.
- Frontend shall include production-grade routing, auth-aware layouts, and error boundaries.

### WA-3 Streamlit Role Boundary

- Existing Streamlit dashboard shall remain supported for internal ops, diagnostics, and rapid prototyping.
- Streamlit shall not be the long-term primary customer-facing application surface.
- Any critical production UX workflows migrated to Next.js shall preserve parity checks against current Streamlit outputs during transition.

### WA-4 API and Streaming Contracts

- Web app backend shall provide REST endpoints for snapshots/history and WebSocket channels for live updates.
- Streaming channels shall cover at minimum orders, fills, positions, PnL, risk state, and incident/kill-switch events.
- API contracts shall enforce explicit schema versioning and backward-compatibility policy.

### WA-5 Data and Session Architecture

- Postgres shall be used as the primary relational application store for web app state/history.
- Redis shall be used for cache/session/rate-limit primitives and short-lived coordination state.
- Web app persistence changes shall preserve existing immutable execution/audit ledger guarantees.

### WA-6 AuthN/AuthZ and Security

- Web app shall implement authenticated access with role-based authorization controls.
- Sensitive endpoints shall enforce least-privilege access and audit logging of privileged actions.
- Session, token, and secret handling shall comply with existing security policy and secret-management requirements.

### WA-7 Reliability and Operability

- Web app services shall expose health/readiness endpoints and structured error telemetry.
- API and streaming surfaces shall include latency/error SLO instrumentation.
- Failure of non-critical web modules shall degrade gracefully without compromising core risk controls.

### WA-8 Frontend Quality and Testing

- Frontend shall include automated unit/integration tests for critical operator workflows.
- End-to-end smoke coverage shall validate login, dashboard load, live stream subscription, and key action paths.
- UI release changes shall be linked to reproducible build artifacts and commit provenance.

### WA-9 Migration and Compatibility

- Migration from current script/Streamlit surfaces to FastAPI/Next.js shall be incremental and non-breaking.
- Existing CLI/script operational workflows shall remain supported until replacement workflows are production-certified.
- Architecture docs and developer onboarding docs shall remain synchronized with migration state.
