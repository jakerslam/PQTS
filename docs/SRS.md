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

## 83. Additional Delta Requirements from External Post Chain (0xCristal, March 11, 2026)

These requirements capture net-new, applicable deltas from the referenced follow-up post and avoid duplication of existing fixed-entry, impulse, and compounding controls in `AR-1..AR-8`.

Observed source links:
- `https://x.com/0xCristal/status/2031736474744545644?s=20`
- Quoted context reference in post body: `Lunar (@LunarResearcher)` (quoted-post mention)

### AR-9 Mid-Probability Entry Band Policy Contract

- Strategy profiles shall support configurable mid-probability entry bands (source-profile example: `0.21` to `0.70`) rather than a single fixed-entry point.
- Entry-policy evaluation shall enforce per-market minimum edge thresholds after fees/slippage for any contract admitted inside the configured band.
- Orders outside the active entry band shall be blocked with explicit policy reason codes and telemetry.

### AR-10 Underlier-Focused Market Scope Contract

- Strategy policies shall support explicit underlier scope gating (source-profile emphasis: `BTC` and `ETH` prediction markets).
- Candidate selection shall reject off-scope underliers unless an approved expansion profile is active.
- Runtime shall report per-underlier exposure, hit rate, and reject/fill quality to validate scope assumptions before expansion.

### AR-11 External-Reference Assimilation Governance Contract

- Any strategy logic adapted from external references (for example Telegram-shared bot recipes) shall be captured as versioned, auditable policy artifacts before execution.
- External-reference-derived rules shall require replay/backtest evidence and risk policy validation before paper/canary promotion.
- Runtime shall persist provenance tags for each rule indicating origin (`internal`, `external_reference`, `hybrid`) and validation status.

### AR-12 Promotional-Claim Quarantine Contract

- Extreme payout screenshots or anecdotal ROI claims from this source chain shall be classified as promotional artifacts and excluded from reference benchmark sets.
- Reference benchmark inclusion shall require reproducible run bundles with full trade-level logs and provenance metadata.
- Claims lacking reproducible evidence shall remain `unverified` and may inform hypothesis generation only.

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

## 84. Additional Delta Requirements from External Post Chain (w1nklerr, March 11, 2026)

These requirements capture net-new, applicable deltas from the referenced follow-up post and avoid duplicating previously-assimilated short-horizon, parity-gap, and copytrade safety controls.

Observed source links:
- `https://x.com/w1nklerr/status/2031771017434042537?s=20`
- `http://t.me/KreoPolyBot?start=ref-defiwinkle` (post body copytrade link)

### WK-11 LLM-Assisted Strategy Authoring Provenance Contract

- Strategy logic drafted with LLM providers (source context: Anthropic-assisted authoring) shall preserve model/provider provenance, prompt hash, and generation timestamp in run artifacts.
- LLM-authored strategy drafts shall require deterministic replay/backtest evidence and risk-policy conformance checks before paper/canary promotion.
- Runtime shall block direct live/canary activation of unreviewed LLM-authored strategy artifacts.

### WK-12 Stage-Level Sub-Second Pipeline Budget Contract

- For short-horizon strategies with sub-second goals, runtime shall track stage-level latency budgets for ingest, probability update, EV/sizing, and order submission.
- Telemetry shall persist per-stage latency distributions and identify bottleneck stage IDs on budget breach.
- Budget breaches shall trigger safe degradation (`hold`, throttle, or disable) instead of continuing with stale decision state.

### WK-13 Copytrade Endpoint Allowlist and Revocation Contract

- Copytrade integrations shall support explicit endpoint allowlists with per-endpoint trust tier, capability scope, and expiry policy.
- Operator controls shall support immediate endpoint revocation/disable with auditable reason and timestamp.
- Trades originating from copytrade pathways shall include endpoint ID provenance for replay, incident triage, and compliance auditing.

## 85. Additional Delta Requirements from External Post Chain (0xashensoul, March 11, 2026)

These requirements capture net-new, applicable deltas from the referenced post focused on real-time geopolitical catalyst detection and lead-time exploitation for event markets.

Observed source links:
- `https://x.com/0xashensoul/status/2031813947343483198?s=20`
- `https://polymarket.com/event/will-the-us-conduct-a-cyberattack-on-iran-by-march-31?via=9999`
- Mentioned signal source in post body: `@glintintel`

### ASH-1 Geopolitical Claim-Event Extraction Contract

- Event-intel ingestion shall support extraction of adversarial attribution/claim events (for example "actor X claimed responsibility for operation Y") with normalized actor, target, and claim-type fields.
- Claim events shall preserve evidence payload pointers, detection timestamp, and source account/provider metadata.
- Ambiguous or conflicting claim parsing shall degrade to `hold` with explicit ambiguity reason codes.

### ASH-2 Signal-Lead Telemetry Contract

- For catalyst-driven markets, runtime shall persist `first_signal_ts`, `first_market_move_ts`, and derived lead-time metrics per opportunity.
- Lead-time analytics shall bucket realized edge by latency window (for example `0-30s`, `30-60s`, `60-120s`, `>120s`) and publish execution-quality attribution.
- Strategies shall auto-throttle when median lead-time edge decays below configured viability thresholds.

### ASH-3 Single-Source Emergency Mode Contract

- When corroboration is unavailable but urgency is high, event-intel execution may enter a constrained single-source mode with stricter limits.
- Single-source mode shall enforce reduced size caps, shorter max hold horizon, and mandatory post-event evidence review.
- Promotion to broader capital allocation requires reproducible evidence that single-source mode remains net-positive after costs and false-positive impact.

### ASH-4 Source Reliability and Claim Handling

- Public claims from this source chain about deterministic minute-scale alpha or extreme short-window ROI shall be marked `unverified` unless backed by reproducible trade-level evidence.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated controls rather than promotional profitability claims.

## 86. Additional Delta Requirements from External Post Chain (obscicron, March 11, 2026)

These requirements capture net-new, applicable deltas from the referenced post focused on low-latency live-speech transcription for mention-market trading.

Observed source links:
- `https://x.com/obscicron/status/2031704141307805947?s=20`
- Mentioned ASR provider in post body: `Deepgram Nova-3`

### OBSC-1 Live Speech Ingestion and ASR Contract

- PQTS shall support ingesting live speech/audio streams for event-market workflows through versioned ASR adapters.
- ASR artifacts shall persist partial and final transcript segments with timestamps, speaker/source identifiers, and provider/model metadata.
- Transcript ingestion shall expose end-to-end ingest-to-transcript latency metrics for replay and SLO enforcement.

### OBSC-2 Mention-Market Trigger Extraction Contract

- Transcript pipelines shall support mention-trigger extraction for configured entities/topics mapped to mention-market instruments.
- Trigger extraction shall preserve matched phrase/entity, confidence score, and text-span evidence for each candidate action.
- Ambiguous or low-confidence mention detections shall default to `hold` unless corroboration thresholds are met.

### OBSC-3 Transcript-to-Order Latency Budget Contract

- Mention-market strategies shall define explicit stage budgets for speech ingest, ASR inference, trigger extraction, and order routing.
- Runtime shall track latency distribution per stage and publish budget-breach diagnostics with bottleneck stage IDs.
- If latency budgets are breached, strategy action shall degrade safely (`hold`/throttle/disable) rather than submitting on stale transcript state.

### OBSC-4 Transcript Quality and Revision-Aware Risk Controls

- Strategy decisioning shall account for partial-to-final transcript revisions and prevent irreversible actions on unstable text segments.
- Actions based on partial transcripts shall require stricter size caps and faster confirmation/exit rules until final transcript confirmation.
- Error rates from ASR revisions (false triggers, retractions) shall be logged and included in promotion-gate evidence.

### OBSC-5 Source Reliability and Claim Handling

- Public claims from this source chain about deterministic speed advantage or extreme short-window profitability shall be marked `unverified` unless supported by reproducible trade-level evidence.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated controls rather than promotional profitability claims.

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

## 43. Additional Requirements from External Repository (virattt/dexter, March 9, 2026)

These requirements are derived from the referenced repository implementation and README:
- `https://github.com/virattt/dexter`
- `https://raw.githubusercontent.com/virattt/dexter/main/README.md`

### DXR-1 Agent Scratchpad Audit Trail

- System shall persist per-run append-only scratchpad logs in JSONL format capturing at minimum: initial query, tool calls (arguments + raw result), and reasoning/decision notes.
- Scratchpad files shall include deterministic run identifiers and timestamps to support incident replay and debugging.
- Scratchpad schema shall support safe parsing of structured tool outputs while preserving raw payload fidelity.

### DXR-2 Anti-Loop Tool Execution Controls

- Agent orchestration shall enforce configurable per-tool soft call limits and query-similarity warnings to reduce retry loops.
- System shall surface loop-risk warnings to the orchestrator before additional tool invocations.
- Orchestrator shall support graceful continuation (warn-first) rather than hard-fail blocking for first-limit breaches.

### DXR-3 Context Overflow Recovery and Memory Flush

- Agent runtime shall enforce token-context thresholds with automatic overflow recovery actions.
- Overflow recovery shall include selective oldest-result pruning with configurable keep-count and bounded retry attempts.
- System shall support optional memory-flush summarization for long runs and emit explicit events when context is compacted.

### DXR-4 Provider-Routed LLM Layer

- LLM subsystem shall support multi-provider routing (cloud and local) behind a single abstraction layer.
- Runtime shall support provider-specific fast-model selection for lightweight sub-tasks while preserving a default high-reasoning model for critical tasks.
- Provider routing failures shall use classified retry/backoff and non-retryable error escalation paths.

### DXR-5 Conditional Tool Registry and Failover

- Tool registry shall support conditional inclusion based on environment capability and key availability.
- Search/data tools shall support ordered fallback chains (primary source -> secondary source -> tertiary source) with explicit provenance on the selected source.
- System prompt/tool metadata shall be generated from registry descriptors to keep runtime behavior and documentation synchronized.

### DXR-6 Skill Package Interface (SKILL.md)

- System shall support workflow skills packaged as `SKILL.md` modules with metadata and executable instructions.
- Skill discovery shall support built-in and project-level skill directories with precedence/override rules.
- Skill metadata shall be exposed to orchestration prompts while full instructions are loaded on invocation.

### DXR-7 Structured Evaluation Harness

- System shall provide an evaluation runner over curated finance/market question datasets with support for full-run and sampled-run modes.
- Evaluation shall support LLM-as-judge scoring with structured output schema and per-example comments.
- Eval UI/CLI shall stream progress and running metrics and persist run metadata for experiment comparisons.

### DXR-8 Messaging Channel Gateway with Access Policies

- System shall support chat-channel gateways beyond Discord/Telegram, including policy-driven direct-message and group-message modes.
- Channel ingress shall enforce explicit allowlists and mention-based triggers for group contexts.
- Gateway credentials, policy config, and debug logs shall be separated from core runtime state with secure local storage paths.

## 44. Additional Requirements from External Repository (financial-datasets/web-crawler, March 9, 2026)

These requirements are derived from the referenced repository implementation and README:
- `https://github.com/financial-datasets/web-crawler`
- `https://raw.githubusercontent.com/financial-datasets/web-crawler/main/README.md`

### WCR-1 Multi-Source Search Adapter Framework

- Research ingestion shall support pluggable search adapters with a shared normalized result schema (`title`, `url`, `published_date`, `source`).
- Search adapters shall execute concurrently with bounded per-source result caps.
- Adapter failures/timeouts shall degrade gracefully without aborting aggregate search output.

### WCR-2 Recency-Normalized Aggregation

- Aggregated search output shall be globally sorted by normalized timestamp with timezone normalization rules.
- Search aggregation shall preserve source attribution for every result.
- Output contracts shall be stable JSON structures suitable for downstream automation.

### WCR-3 Canonical URL Resolution

- Ingestion shall resolve wrapped/redirected news links into canonical destination URLs before downstream parsing.
- Canonicalization shall include source-specific decoders where needed (for example news feed redirect wrappers).
- Fallback behavior shall preserve original URLs when canonical resolution fails.

### WCR-4 Robust JS-Heavy Page Parsing Pipeline

- Parser subsystem shall support JavaScript-rendered pages via headless-browser rendering fallback.
- Parsing flow shall include consent/overlay dismissal attempts, lazy-content autoscroll, and readability-focused main-content extraction.
- Parser shall fall back through semantic selectors to full-body extraction when high-quality article parsing fails.

### WCR-5 Link Graph Extraction Capability

- Parser subsystem shall support extraction of normalized absolute links from rendered pages for citation expansion and crawl traversal.
- Link filtering shall drop non-navigational targets (for example `javascript:`, `mailto:`, fragment-only).
- Link extraction shall deduplicate and return sorted outputs for deterministic downstream behavior.

### WCR-6 Resource and Session Controls for Ingestion

- Search/parsing clients shall use explicit timeout budgets, connection-pool limits, and per-host concurrency bounds.
- Ingestion services shall support async context-managed session lifecycle to prevent socket/session leaks.
- Runtime shall support user-agent/header policies configurable by source connector.

### WCR-7 Parse Output Quality Contract

- Parsed document outputs shall include at minimum `url`, `title`, `content`, and `content_length`.
- Parsers shall normalize whitespace and encoding artifacts before emitting content payloads.
- Parsing jobs shall emit explicit failure modes/errors for unsupported or blocked pages.

### WCR-8 Real-Site Integration Test Coverage

- Test suite shall include integration tests against representative real-world financial/news pages for both link extraction and content extraction.
- Integration tests shall assert minimum extraction-quality thresholds (non-empty content, minimum link counts).
- Tests that depend on external network sources shall be isolated and explicitly labeled in CI.

## 45. Additional Requirements from External Repository (financial-datasets/llm-evaluations, March 9, 2026)

These requirements are derived from the referenced repository implementation and experiment packs:
- `https://github.com/financial-datasets/llm-evaluations`
- `https://raw.githubusercontent.com/financial-datasets/llm-evaluations/main/README.md`

### LLE-1 Task-Specific Evaluation Packs (Classification + Regression)

- System shall support evaluation packs by task family, including at minimum binary risk classification and numeric financial-value regression tasks.
- Each evaluation pack shall define task-specific prompt templates, dataset schema, output schema, and scoring logic.
- Evaluation packs shall remain independently runnable and comparable under a shared results contract.

### LLE-2 Strict Structured Output Contract for Model Judgments

- Evaluation runs shall require model outputs through strict structured function/tool-call schemas (no free-form parse dependence for primary scoring fields).
- Structured outputs shall be validated against typed schemas before scoring.
- Invalid or missing structured responses shall be recorded as explicit failed predictions with reason codes.

### LLE-3 Provider-Parity Tool Calling Layer

- Multi-provider evaluation runtime shall normalize tool/function-calling semantics across model providers while preserving provider-specific transport formats.
- Runtime shall keep one canonical logical tool schema per task and derive provider-specific definitions from that canonical schema.
- Provider adapters shall expose normalized prediction objects for downstream scoring irrespective of provider API differences.

### LLE-4 Cost and Latency as First-Class Evaluation Metrics

- Every prediction record shall include token-cost estimate and wall-clock duration.
- Aggregate reports shall include per-model average cost and average duration alongside quality metrics.
- Model ranking views shall support cost-quality and latency-quality tradeoff comparisons, not quality-only ranking.

### LLE-5 Dual Artifact Output (Metrics + Raw Predictions)

- Evaluation runs shall emit at least two timestamped artifacts:
  - aggregated metrics summary,
  - raw per-sample prediction records for manual audit.
- Raw prediction artifacts shall include model, ticker/entity ID, ground truth, predicted value/label, and reasoning trace fields.
- Artifact naming shall be deterministic and machine-ingestable for longitudinal benchmarking.

### LLE-6 Best-Model Selection per Metric Family

- Evaluation subsystem shall compute best-model winners per relevant metric family rather than a single global winner.
- For classification tasks, best-model selection shall include accuracy and F1 winners.
- For regression tasks, best-model selection shall include low-error winners (for example MAE/RMSE) and tolerance-based accuracy winners.

### LLE-7 Tolerance-Banded Regression Accuracy

- Regression scoring shall include percentage-within-error-band metrics (for example within 5%, 10%, and 20% of ground truth).
- Scoring shall include safeguards for zero-denominator cases in percentage-based error metrics.
- Regression outputs shall include MAE, MSE/RMSE, MAPE, and R² in a unified report contract.

### LLE-8 Confusion-Matrix-Native Classification Scoring

- Classification scoring shall include full confusion-matrix breakdown (TP, FP, TN, FN) in addition to accuracy, precision, recall, and F1.
- Metric computation shall be robust to low-sample and degenerate-class distributions.
- Reports shall expose both absolute counts and normalized rates for diagnostic review.

### LLE-9 Dataset Factory + Local Cache Strategy

- Evaluation datasets shall support factory-style construction with optional local JSON caching for reproducibility and rerun speed.
- When cache exists, dataset loaders shall prefer cached snapshots unless explicit refresh is requested.
- Dataset metadata shall include sample counts and label/feature coverage summaries.

### LLE-10 Hypothesis-Driven Financial Label Construction

- Risk-label datasets shall support configurable rule/filter templates used to generate positive/negative classes from financial metrics.
- Label-construction rules shall be versioned and persisted with dataset artifacts so benchmark labels are reproducible.
- System shall record source metric snapshots used to assign each label for auditability.

### LLE-11 Hierarchical Financial Extraction Workflow (XBRL-Oriented)

- Numeric extraction benchmarks shall support hierarchical resolution policies:
  - direct tag extraction,
  - formula-based computation,
  - controlled imputation fallback.
- Prediction artifacts shall include method used, formula/tag provenance, reasoning text, and confidence level.
- Scoring shall permit method-level diagnostics to identify where extraction pipelines fail (direct vs formula vs imputation).

## 46. Additional Requirements from External Repository (virattt/ai-hedge-fund, March 9, 2026)

These requirements are derived from the referenced repository implementation and web/backend architecture:
- `https://github.com/virattt/ai-hedge-fund`
- `https://raw.githubusercontent.com/virattt/ai-hedge-fund/main/README.md`

### AHF-1 Runtime-Composable Agent Graphs

- System shall support runtime composition of decision workflows from graph nodes/edges rather than fixed hardcoded pipelines.
- Graph composition shall support multiple analyst nodes feeding shared or dedicated risk/portfolio manager nodes.
- Runtime shall support stable mapping between UI graph node IDs and executable agent functions.

### AHF-2 Strategy Flow Templates and Versioned Persistence

- System shall persist strategy workflow definitions (nodes, edges, viewport/layout metadata, and config data) as versioned flow artifacts.
- System shall support template-marked flows for reuse, duplication, and modification without mutating originals.
- Flow search/list APIs shall provide lightweight summaries separate from full graph payload retrieval.

### AHF-3 Execution Run Registry with Lifecycle Status

- System shall persist execution runs per strategy flow with explicit lifecycle statuses (`IDLE`, `IN_PROGRESS`, `COMPLETE`, `ERROR`).
- Run records shall include request payload snapshots, result payloads, error messages, and start/complete timestamps.
- Runs shall include monotonically increasing per-flow run numbers for ordered auditability.

### AHF-4 Per-Cycle Session Telemetry for Continuous Modes

- System shall support sub-run cycle records for continuous/advisory modes, including cycle-level analyst signals, decisions, and portfolio snapshots.
- Cycle telemetry shall include execution counters (LLM calls, market/API calls) and estimated cost fields.
- Cycle records shall capture trigger context (for example manual, scheduled, market-event).

### AHF-5 Server-Sent Event Streaming for Operator UX

- API layer shall stream execution progress via SSE for both one-shot decision runs and multi-day backtests.
- Streaming protocol shall emit typed events for start, progress updates, errors, and completion payloads.
- Streaming execution shall support client-disconnect detection and cooperative cancellation of in-flight tasks.

### AHF-6 Per-Agent Model Routing Overrides

- Requests shall support per-agent model/provider overrides with fallback to global model defaults.
- Agent model routing shall match unique graph node IDs while also supporting base-agent-key fallback mapping.
- Runtime shall preserve provider-specific model constraints while normalizing the execution contract across agents.

### AHF-7 Deterministic Trade Feasibility Pre-Checks

- Portfolio decisioning shall include deterministic action-feasibility computation prior to LLM action selection.
- Feasibility layer shall enforce action allowlists and max quantities from cash, margin, and position constraints.
- System shall pre-fill forced-hold decisions when no valid trade action is feasible, reducing unnecessary LLM calls.

### AHF-8 Integrated Long/Short + Margin Accounting Model

- Portfolio state model shall support concurrent long and short books per symbol with separate cost bases and realized PnL ledgers.
- Short lifecycle shall explicitly track per-position and aggregate margin usage, release, and cover-cost accounting.
- Portfolio valuation shall compute net liquidation value from cash + longs - shorts with exposure decomposition.

### AHF-9 Volatility and Correlation-Aware Position Limits

- Risk layer shall compute position limits from volatility-adjusted base sizing and correlation-based concentration multipliers.
- Risk output shall include explanatory diagnostics (volatility metrics, correlation stats, applied multipliers, and remaining limit).
- Risk limits shall degrade safely under missing market data with explicit fallback assumptions.

### AHF-10 Hybrid Signal Fabric with Reasoning Artifacts

- System shall support combining deterministic quantitative signal engines with selective LLM classification where source data is incomplete.
- Signal aggregation shall emit structured reasoning payloads including component metrics, weights, and final signal/confidence.
- Runtime shall cap selective LLM enrichment calls (for example partial-article sentiment backfills) for cost control.

### AHF-11 Backtest Progression with Benchmark Context

- Backtest engine shall support business-day iterative simulation with configurable lookback windows and daily decision/execution loops.
- Backtest reporting shall include benchmark-relative performance context (for example buy-and-hold baseline return series).
- Engine shall support partial-result recovery/reporting on interruption for long-running simulations.

### AHF-12 API Key Vault Operations for Multi-Provider Runtime

- System shall support API-key CRUD operations by provider with activate/deactivate semantics and last-used tracking.
- Runtime requests without inline keys shall support automatic hydration from managed key storage.
- Key-management responses shall provide summary-safe views that avoid exposing secrets by default.

## 47. Additional Requirements from External Repository (virattt/openbb-financialdatasets-backend, March 9, 2026)

These requirements are derived from the referenced repository implementation and backend integration patterns:
- `https://github.com/virattt/openbb-financialdatasets-backend`
- `https://raw.githubusercontent.com/virattt/openbb-financialdatasets-backend/main/README.md`

### OBBFD-1 Deterministic API-Key Resolution Precedence

- Data-connector request handling shall resolve provider credentials in strict precedence order: request-header override first, environment default second.
- Protected endpoints shall return explicit `401` responses with remediation guidance when no credential source is available.
- Auth telemetry shall record credential source used (header vs env) without logging raw secrets.

### OBBFD-2 UI-Boot Degraded Mode for Option Endpoints

- UI-critical option endpoints shall support degraded-mode responses when provider auth or upstream data is unavailable.
- Degraded-mode responses shall return deterministic empty/default option payloads instead of transport/server exceptions.
- Frontend contracts shall distinguish degraded option responses from successful upstream-backed responses.

### OBBFD-3 Decorator-Driven Widget Registry Contract

- API layer shall support metadata decorators that co-locate endpoint logic and widget registration metadata.
- System shall auto-build a widgets catalog endpoint from registered metadata without manual duplicate declarations.
- Widget registry validation shall enforce unique endpoint/widget IDs and required metadata fields at startup.

### OBBFD-4 Declarative Workspace/App Manifest Endpoint

- Backend shall expose a declarative app/workspace manifest endpoint (apps/tabs/layout/state metadata) consumed by the dashboard shell.
- Manifest schema shall support tab definitions, layout coordinates, default parameter values, and table/chart view state.
- Manifest contract shall be versioned for backward compatibility across frontend releases.

### OBBFD-5 Financial Table Normalization + Transposition Layer

- Financial statement/metric payload normalization shall support transposing provider-native records into metric-row, period-column table format.
- Normalization shall canonicalize period date formats and maintain deterministic metric ordering for reproducible diffs and tests.
- Transformation layer shall apply consistent numeric formatting and omit provider-specific noise fields from UI responses.

### OBBFD-6 Standardized Parameter Options Endpoints

- Parameter option endpoints shall return consistent `{label, value}` objects for symbols, investors, and other selector domains.
- Options responses shall support deterministic sort ordering and user-friendly label normalization.
- Option endpoints shall define fallback seeds for essential selectors so strategy UIs remain usable during provider outages.

### OBBFD-7 Provider Proxy Reliability Envelope

- Upstream provider proxy endpoints shall propagate meaningful status codes while wrapping errors in a consistent PQTS error schema.
- Provider adapters shall implement timeout and retry policy controls for idempotent read endpoints.
- Runtime shall emit provider latency and upstream-failure telemetry for connector-level SLO monitoring.

### OBBFD-8 Health and Deployment SLO Integration

- Service shall expose a `/health` endpoint designed for orchestrator and CI smoke-check integration.
- Deployment profiles shall define explicit concurrency thresholds, graceful shutdown timeout, and automatic rollback/start-stop controls.
- Runtime configuration shall support container-first deployment targets with stable default service ports.

### OBBFD-9 Real-Time Subscription Session Registry (Optional Module)

- Real-time modules shall maintain connection and subscription registries keyed by session/connection ID.
- Subscription lifecycle shall include deterministic cleanup on disconnect to prevent orphan session state.
- Real-time streaming contracts shall support multi-symbol subscription updates under bounded connection limits.

## 48. Additional Requirements from External Repository (czyssrs/FinQA, March 9, 2026)

These requirements are derived from the referenced repository implementation and benchmark design:
- `https://github.com/czyssrs/FinQA`
- `https://raw.githubusercontent.com/czyssrs/FinQA/master/README.md`

### FINQA-1 Two-Stage Retrieval-to-Reasoning Pipeline Contract

- Quant reasoning workflows shall support an explicit two-stage architecture: evidence retrieval first, executable reasoning program generation second.
- Stage boundaries shall be materialized as versioned intermediate artifacts so each stage can be trained, tested, and swapped independently.
- End-to-end inference mode shall support orchestration across both stages without bypassing stage-level audit logs.

### FINQA-2 Unified Multi-Source Evidence Model (Text + Table)

- Evidence model shall represent both narrative text segments and table rows under one retrieval contract.
- Evidence references shall use stable typed IDs (for example `text_i`, `table_j`) that are preserved through ranking, conversion, and evaluation.
- QA/trade-decision artifacts shall preserve raw source context plus retrieved evidence provenance.

### FINQA-3 Retrieval Quality Metrics with Top-K Recall Reporting

- Retriever evaluation shall report top-k evidence recall metrics (including at least top-3 and top-N configured values) against annotated supporting facts.
- Retrieval outputs shall persist both shortlisted items and full ranked lists for error analysis.
- Metrics shall be computed per example and aggregated corpus-wide for leaderboard comparability.

### FINQA-4 Context Packing Under Token/Length Budgets

- Generator input builder shall enforce configurable evidence-count and token-length budgets when assembling retrieved context.
- Context packing shall preserve deterministic source ordering (narrative pre-text, table evidence, narrative post-text) to reduce nondeterministic behavior.
- Training mode shall guarantee inclusion of gold evidence before adding highest-scoring negatives within remaining budget.

### FINQA-5 Executable Program DSL for Numeric Reasoning

- Reasoning subsystem shall support an executable DSL for arithmetic/comparison and table-aggregation operations.
- Program runtime shall support constants and intermediate step references (for example step-pointer tokens) with strict syntax validation.
- Program outputs shall terminate with explicit end-of-program token conventions for deterministic decoding/evaluation.

### FINQA-6 Dual Accuracy Regime: Execution vs Program Equivalence

- Evaluation shall report both execution accuracy (final numeric/boolean result correctness) and program accuracy (symbolic equivalence to reference program).
- Program equivalence checks shall support algebraic simplification so mathematically equivalent operation sequences are treated as correct.
- Evaluation shall produce error bundles containing source, prediction, and execution traces for failed examples.

### FINQA-7 Blind-Test Benchmark Governance

- Benchmark design shall include public validation/test sets and at least one private/blind test split for anti-overfitting governance.
- Private test execution mode shall run full pipeline inference without access to intermediate gold annotations.
- Submission/output formats for public and private evaluation shall be strictly schema-validated before scoring.

### FINQA-8 Leakage-Resistant Data Transformation Controls

- Table-to-text and context-normalization transforms shall be treated as versioned, test-covered components due to leakage risk.
- Dataset preprocessing shall include regression tests that detect label leakage, schema drift, and positive/negative formatting inconsistencies.
- Changes to preprocessing functions shall require benchmark reruns and explicit result version bumps.

### FINQA-9 Program Representation Compatibility (Sequential + Nested)

- Reasoning module shall support both sequential and nested program representations with deterministic conversion utilities.
- Evaluation tooling shall correctly normalize both representations before execution and symbolic-equivalence checks.
- Artifact schema shall persist canonical and representation-specific program forms for reproducibility.

### FINQA-10 Prediction Artifact Standardization for External Leaderboards

- Prediction export format shall be standardized as ID-keyed program token lists suitable for external leaderboard ingestion.
- Export validators shall enforce token grammar, required terminal token, and deterministic ordering across runs.
- Benchmark outputs shall include machine-readable summaries of retrieval and reasoning metrics in addition to raw predictions.

## 49. Additional Requirements from External Post (k1rallik + linked RohOnChain breakdown, March 9, 2026)

These requirements are distilled from the referenced post and the article link it points to:
- `https://x.com/k1rallik/status/2030957511260491994`
- `https://x.com/RohOnChain/status/2029998336837890193`

### PMDESK-1 Layered Desk Runtime Separation

- System architecture shall separate research/modeling, execution, risk control, and platform operations into independent runtime modules.
- Module boundaries shall be enforced through explicit interfaces so each layer can be tested and deployed independently.
- Runtime telemetry shall report per-layer health and latency to localize failures rapidly.

### PMDESK-2 Bayesian Probability Update Engine

- Probability engine shall support continuous Bayesian posterior updates from multi-source evidence streams.
- Model layer shall persist prior, evidence, posterior, and confidence metadata for every market update cycle.
- Update pipeline shall support configurable evidence weighting and source reliability calibration.

### PMDESK-3 Cross-Market Dependency Graph Enforcement

- System shall represent related markets in a dependency graph and enforce logical probability constraints between connected contracts.
- Constraint engine shall emit actionable arbitrage/consistency alerts when relationships are violated.
- Graph checks shall run pre-trade and post-trade with auditable violation records.

### PMDESK-4 Calibration Surface and Bias Diagnostics

- Research subsystem shall maintain calibration surfaces mapping quoted probabilities to realized outcome frequencies by regime/bucket.
- Diagnostics shall flag persistent mispricing patterns (for example longshot or favorite bias) and feed strategy parameter updates.
- Calibration reports shall be versioned and published as reproducible artifacts.

### PMDESK-5 Uncertainty-Adjusted Kelly Sizing

- Position-sizing engine shall support Kelly-based allocation adjusted by model uncertainty (for example edge-variance penalty).
- Sizing policy shall include hard caps, fractional-Kelly controls, and minimum-edge thresholds before order generation.
- Every position decision shall persist sizing inputs (edge, uncertainty factor, cap applied, final size) for auditability.

### PMDESK-6 Microstructure-Aware Execution Algorithms

- Execution subsystem shall support order-slicing algorithms (VWAP/TWAP and depth-aware variants) to minimize market impact.
- Execution quality monitoring shall track slippage vs target benchmark and time-to-fill per order slice.
- Local orderbook state shall include sequence-gap detection and deterministic recovery on stream desynchronization.

### PMDESK-7 Informed-Flow and Liquidity Kill Switches

- Risk engine shall compute informed-flow/liquidity stress indicators (including VPIN-style metrics) in real time.
- Configurable thresholds shall trigger automated protective actions (widen quotes, reduce size, or withdraw quotes).
- Trigger events shall generate operator alerts and immutable incident records with metric snapshots.

### PMDESK-8 Portfolio Risk Guardrails (VaR + Drawdown)

- Portfolio risk shall include rolling VaR estimates, drawdown tracking, and scenario stress checks across active books.
- System shall automatically gate new risk when drawdown or VaR limits breach configured thresholds.
- Risk controls shall fail safe on missing inputs by reducing exposure rather than continuing at prior risk levels.

### PMDESK-9 Cross-Venue Price Discovery and Latency Arb Module

- Data layer shall ingest and normalize prices/odds across multiple venues for shared-event contracts.
- Strategy layer shall detect and score temporary cross-venue dislocations after fee, latency, and settlement-cost adjustments.
- Execution planner shall support hedged two-leg routing with venue-specific collateral/liquidity constraints.

### PMDESK-10 On-Chain Settlement-Aware Monitoring

- For on-chain venues, system shall support mempool/block-event monitoring relevant to market state transitions and resolution flow.
- Settlement-aware controls shall tighten risk or accelerate exits as resolution state uncertainty increases.
- Blockchain integration shall support self-hosted or managed RPC endpoints with health and failover monitoring.

### PMDESK-11 Event-Driven Data Backbone Requirements

- Platform shall support an event-driven ingestion backbone with durable stream semantics for market, order, and risk events.
- Time-series storage shall preserve high-frequency orderbook/trade snapshots with replay capability for backtests and incident forensics.
- Caching layer shall provide low-latency state retrieval while maintaining consistency guarantees for execution-critical paths.

### PMDESK-12 Infrastructure and Reliability Baseline

- Deployment architecture shall be containerized with orchestrator-native autoscaling and zero-downtime rollout controls.
- Secrets and key material shall be managed via dedicated secret-management services with rotation policies.
- Production SLO targets shall include explicit uptime and latency objectives, plus alerting on objective breaches.

## 50. Additional Requirements from External Repository (virattt/financial-agent-ui, March 9, 2026)

These requirements are derived from the referenced repository implementation and UI-agent integration patterns:
- `https://github.com/virattt/financial-agent-ui`
- `https://raw.githubusercontent.com/virattt/financial-agent-ui/main/README.md`

### FAUI-1 Tool-Aware Generative UI Rendering Contract

- Agent runtime shall emit structured tool-call metadata with stable tool type identifiers consumable by the frontend.
- Frontend shall maintain a registry mapping each supported tool type to both loading-state and final-state UI components.
- Unknown tool types shall degrade to a safe generic renderer rather than breaking the chat UI.

### FAUI-2 Stream-Event-Driven Chat Orchestration

- Chat interface shall stream model token chunks incrementally while preserving final message integrity.
- Tool invocation lifecycle shall be event-driven: show loading UI at tool-call detection, then atomically replace with final rendered output.
- Client runtime shall persist terminal event outputs into conversation history for follow-up turns.

### FAUI-3 Remote Runnable API Boundary

- Frontend shall communicate with the agent backend through a single remote runnable endpoint with explicit input/output schemas.
- Input contract shall support role-tagged chat message history plus current user prompt.
- Output contract shall support both direct natural-language answers and structured tool-result payloads.

### FAUI-4 Graph Node Event Contract Stability

- Backend graph node names and node output keys shall be treated as versioned API contracts for frontend event handlers.
- Contract changes shall require synchronized frontend/backend updates and compatibility tests.
- Event parsing shall validate node identity and payload shape before UI mutation.

### FAUI-5 Strongly Typed Tool Argument Schemas

- Every tool shall define explicit typed argument schemas, including defaults and domain constraints.
- Financial query tools shall use constrained enumerations for line-item fields to reduce invalid/ambiguous requests.
- Tool schemas shall be reused for LLM function binding, request validation, and API documentation.

### FAUI-6 Multi-Source Financial + Web Retrieval Surface

- Agent tool layer shall support both structured financial data retrieval and open-web/news retrieval in one orchestration surface.
- Tool selection policy shall prioritize structured financial endpoints for factual metrics and web retrieval for recent/contextual updates.
- Cross-source results shall expose provenance metadata so users can distinguish dataset facts from web findings.

### FAUI-7 UI-Native Data Shape Normalization

- Tool responses shall be normalized into UI-native shapes for charts, tabular financials, and citation/result cards.
- Presentation normalization shall include deterministic date formatting and numeric/currency formatting rules.
- Normalization layer shall avoid mutating shared raw payloads used for downstream logic or audit trails.

### FAUI-8 Progressive Loading Components per Tool Type

- Each renderable tool shall include a dedicated skeleton/loading component to preserve responsiveness during tool latency.
- Loading components shall mirror expected final layout sufficiently to minimize reflow.
- Tool completion shall replace placeholders in place, preserving message ordering.

### FAUI-9 Structured Error Envelope for Tool Failures

- Tool wrappers shall return structured error envelopes for recoverable upstream/request failures instead of uncaught exceptions.
- UI layer shall render tool errors as explicit, non-crashing message blocks with actionable remediation hints.
- Error payloads shall include tool name, failure category, and minimal debug context without exposing secrets.

### FAUI-10 Frontend/Backend Local Compose Development Contract

- Development stack shall provide one-command multi-service startup with explicit frontend↔backend service wiring.
- Runtime configuration shall externalize backend endpoint URLs via environment variables, with sensible localhost defaults.
- Backend CORS policy shall be environment-aware and default-safe for local development origins.

### FAUI-11 Agent Run Observability and Trace Correlation

- Agent execution shall expose trace instrumentation hooks for model and tool calls, including run IDs and step-level timing.
- Frontend stream event run IDs shall be correlatable with backend tracing to debug latency/errors end-to-end.
- Observability configuration shall be environment-gated to avoid accidental production leakage of sensitive traces.

### FAUI-12 Extensible Tool-and-Component Plugin Path

- Adding a new tool shall follow a standard extension path: backend tool + schema, graph/tool registry, frontend component mapping.
- Build/test checks shall verify one-to-one mapping between enabled backend tools and frontend render handlers.
- Plugin extension workflow shall support incremental additions without rewriting core chat orchestration.

## 51. Additional Requirements from External Repository (virattt/financial-datasets, March 9, 2026)

These requirements are derived from the referenced repository implementation and dataset-generation architecture:
- `https://github.com/virattt/financial-datasets`
- `https://raw.githubusercontent.com/virattt/financial-datasets/main/README.md`

### FDATA-1 Multi-Source Financial Corpus Ingestion

- Dataset generation subsystem shall support ingestion from raw text lists, PDF URLs, 10-K filings, and 10-Q filings through one unified API surface.
- Each ingestion mode shall normalize extracted text into a common downstream chunking interface.
- Ingestion failures for one source document shall not abort batch generation for unrelated documents.

### FDATA-2 SEC Filing Identity + Access Compliance

- SEC filing retrieval workflows shall require explicit requester identity configuration for compliant EDGAR access.
- Filing adapters shall validate ticker/year/quarter inputs before submitting remote requests.
- System shall emit clear retrieval errors when no matching filing exists for the requested period.

### FDATA-3 Filing Item-Scoped Extraction Controls

- Filing extraction shall support optional item-scoped retrieval (for example selected 10-K/10-Q item sections) to target specific domains.
- Item selectors shall be validated against an enumerated allowlist to prevent invalid section references.
- Extraction outputs shall preserve requested item ordering when sections are present.

### FDATA-4 Deterministic Text Cleanup Pipeline

- Preprocessing shall normalize filing text by removing newline artifacts and repetitive delimiter noise before model prompting.
- Cleanup transforms shall be deterministic and versioned to preserve dataset reproducibility across reruns.
- Preprocessing changes shall require regeneration/version bump of dependent datasets.

### FDATA-5 Token-Aware Chunking with Overlap

- Dataset generator shall use token-based chunking with configurable chunk size and chunk overlap controls.
- Chunking policy shall be shared across source types to keep prompt payload sizing behavior consistent.
- Chunk metadata shall include chunk index and source reference fields for traceability.

### FDATA-6 Question Budget Allocation Policy

- Max-question targets shall be allocated across chunks/sources with deterministic base allocation and remainder distribution.
- Generator shall stop once the global question budget is reached, even when additional chunks remain.
- Final output shall be truncated/validated to respect the requested maximum question count.

### FDATA-7 Structured LLM Function-Call Output Contract

- Generation calls shall use strict function/tool schemas for dataset items (`question`, `answer`, `context`) rather than free-form text parsing.
- Tool-call argument parsing shall validate schema compliance before dataset items are accepted.
- Invalid or empty tool-call payloads shall be skipped with non-fatal warnings.

### FDATA-8 Grounded, Standalone Q/A Quality Policy

- Prompt policy shall enforce standalone question-answer generation that is fully answerable without external document references.
- Quality checks shall reject examples that reference source-document framing (for example “according to the document” style phrasing).
- Every dataset item shall include supporting context text sufficient to justify the answer.

### FDATA-9 Provider Guardrails and Retry Strategy

- Model provider routing shall enforce explicit support constraints (for example supported model families) at generator initialization time.
- LLM request execution shall include bounded retry with exponential backoff for transient provider failures.
- Per-chunk generation failures shall be isolated so remaining chunks continue processing.

### FDATA-10 Canonical Dataset Schema and Validation

- Generated outputs shall conform to a canonical typed schema for downstream training/evaluation ingestion.
- Schema validation shall run prior to persistence/export and reject malformed items.
- Dataset exports shall remain stable JSON-serializable objects suitable for benchmark tooling and fine-tuning pipelines.

### FDATA-11 Generation Provenance and Usage Telemetry

- Dataset artifacts shall persist generation provenance including model name, prompt version, source mode, and chunking parameters.
- Generation runs shall track token usage metrics (prompt/completion) and item yield statistics.
- Provenance metadata shall support reproducibility audits and cost/performance tuning.

### FDATA-12 Synthetic Financial QA Regression Tests

- Test suite shall include regression checks for parser behavior (10-K/10-Q item retrieval and filtering) and generator output constraints.
- Integration tests shall verify end-to-end generation paths across representative source modes.
- CI quality gates shall ensure dataset-generation changes do not silently break schema or retrieval behavior.

## 52. Additional Requirements from External Repository (sullyo/fingen, March 9, 2026)

These requirements are derived from the referenced repository implementation and chat-agent UI architecture:
- `https://github.com/sullyo/fingen`
- `https://raw.githubusercontent.com/sullyo/fingen/main/README.md`

### FINGEN-1 Server-Action AI Runtime with Split UI/Model State

- Chat runtime shall maintain separate AI state (canonical conversation/tool context) and UI state (render nodes) to support responsive rendering without losing model history integrity.
- Server actions shall own authoritative message appends for both user and assistant turns.
- State model shall include stable message IDs and role fields for reproducible replay/debugging.

### FINGEN-2 Optimistic User-Turn Rendering

- Frontend shall optimistically render user messages before backend completion to reduce perceived latency.
- Optimistic updates shall preserve message ordering with eventual server-confirmed assistant/tool output append.
- Failed request paths shall reconcile optimistic state with explicit error/rollback handling.

### FINGEN-3 Unified Event Stream Handling for LLM + Tools

- Runtime shall process streamed agent events and branch handling by event type (LLM token stream, tool start, tool end, run end).
- LLM token deltas shall update incremental text streams while tool events render structured UI blocks in the same assistant turn.
- Event handler framework shall support append-only incremental UI composition during a single run.

### FINGEN-4 Tool Invocation Transparency UI

- Chat UI shall expose tool invocation badges showing tool name and parsed argument payloads.
- Tool invocation and completion states shall be visually distinct to improve operator trust/debuggability.
- Tool argument displays shall be sanitized to avoid leaking sensitive fields.

### FINGEN-5 Tool-Result-to-Widget Routing

- Tool outputs shall be routed to dedicated widget renderers by tool name/type (for example chart, news carousel, financial dialog).
- Widget routing shall include deterministic fallback behavior when output schema is missing or invalid.
- Tool renderer contracts shall be versioned and validated against backend output schemas.

### FINGEN-6 Financial Data Adapter Layer (Polygon-Style)

- Data adapters shall encapsulate external market/news/financial provider calls behind typed internal functions.
- Adapter layer shall validate provider response status and normalize payloads before returning to agent tools.
- Adapters shall support minimal-field filtering for high-noise endpoints to reduce token/UI bloat.

### FINGEN-7 Structured Tool Schemas for Agent Reliability

- Agent tools shall define explicit structured schemas for required query inputs (ticker, date range, etc.).
- Tool descriptions shall encode intent guidance so the planner selects the right tool for each query type.
- Schema validation failures shall return user-safe errors and skip unsafe tool execution.

### FINGEN-8 Message-Role Conversion Contract

- Chat systems shall provide deterministic conversion between app-level message roles and framework-level message primitives.
- Conversion logic shall preserve tool-call metadata across turns for correct multi-step reasoning continuity.
- Unsupported role values shall fail fast with explicit errors.

### FINGEN-9 Rich Markdown Rendering with Data-Oriented Components

- Assistant text renderer shall support GitHub-flavored markdown, tables, lists, and code blocks with syntax rendering.
- Citation/link rendering shall support external-link safety defaults (`noopener`, `noreferrer`).
- Render pipeline shall handle streaming text updates without reflowing prior completed content.

### FINGEN-10 Input UX Controls for High-Velocity Chat

- Composer shall support Enter-to-submit and Shift+Enter newline behavior with IME-safe handling.
- Chat UI shall include sticky input placement and optional starter prompt templates to reduce cold-start friction.
- Input submission shall trim empty payloads and prevent duplicate sends.

### FINGEN-11 Scroll Anchoring and Navigation in Streaming Chats

- Chat interface shall track whether the user is at the bottom and auto-scroll only when appropriate.
- System shall provide explicit “scroll to latest” affordances when new content arrives while the user is reading older messages.
- Scroll logic shall use viewport/visibility signals to avoid disruptive jumps during streaming updates.

### FINGEN-12 Multi-Modal Assistant Turn Composition

- A single assistant turn shall support interleaving narrative text plus multiple structured artifacts (badges, charts, tables/cards).
- Turn-composition model shall preserve deterministic ordering of emitted artifacts based on event chronology.
- Persisted conversation history shall store a text summary of tool outputs sufficient for follow-up context.

## 53. Additional Requirements from External Repository (AdamGetbags/secAPI, March 9, 2026)

These requirements are derived from the referenced repository implementation and SEC endpoint usage pattern:
- `https://github.com/AdamGetbags/secAPI`
- `https://raw.githubusercontent.com/AdamGetbags/secAPI/main/secFilingScraper.py`

### SECAPI-1 SEC-Compliant Request Identity Policy

- SEC data ingestion requests shall include an explicit requester identity `User-Agent` header for compliant API access.
- Identity configuration shall be externally configurable and required at runtime.
- Missing identity configuration shall fail fast before outbound SEC requests.

### SECAPI-2 Master Ticker-to-CIK Registry Ingestion

- System shall ingest and parse the SEC company ticker master dataset (`company_tickers.json`) as a canonical issuer map.
- Registry ingestion shall support dictionary-indexed SEC payload formats and normalize them into tabular records.
- Registry snapshots shall expose ticker, company title, and CIK fields for downstream joins.

### SECAPI-3 Canonical CIK Normalization Contract

- CIK handling shall support both integer and zero-padded 10-digit string representations.
- SEC endpoint clients shall use zero-padded CIK format when constructing submissions/XBRL URLs.
- Normalization utilities shall be centralized to avoid inconsistent per-module formatting.

### SECAPI-4 Company Submissions Metadata Pipeline

- Filing metadata ingestion shall pull company submissions from `data.sec.gov/submissions/CIK{cik}.json`.
- Recent filing collections shall be normalized to structured tabular form including accession number, form type, and report date.
- Metadata layer shall support deterministic filtering/slicing by form class (for example 10-Q/10-K).

### SECAPI-5 XBRL Company Facts Taxonomy Traversal

- Fundamentals ingestion shall support `companyfacts` endpoint traversal across available taxonomies (for example `dei`, `us-gaap`).
- Data model shall preserve taxonomy, concept name, unit family, filing form, and reporting period metadata.
- Parsers shall handle variable concept coverage across issuers without crashing on missing tags.

### SECAPI-6 Concept-Level Time-Series Endpoint Support

- System shall support direct concept queries via `companyconcept` endpoint for targeted metric extraction.
- Concept responses shall be normalized into time-series records with value, unit, form, filing, and period fields.
- Concept extraction APIs shall validate taxonomy/concept identifiers before request execution.

### SECAPI-7 Unit-Aware Metric Extraction

- XBRL extraction shall be unit-aware (for example `USD`, `shares`) and preserve unit labels in downstream datasets.
- Metric accessors shall support selecting preferred unit families while retaining alternates for auditability.
- Unit mismatch conditions shall be surfaced explicitly rather than silently coerced.

### SECAPI-8 Form-Scoped Series Derivation

- Time-series builders shall support form-scoped slicing (for example 10-Q-only or 10-K-only series) for consistent comparability.
- Derived series shall support index reset/reordering and chronological plotting/analysis workflows.
- Form filters shall remain configurable to support custom screening sets beyond 10-Q/10-K.

### SECAPI-9 Tabular Normalization for Analytics Pipelines

- JSON payloads from SEC endpoints shall be convertible to stable tabular schemas suitable for analytics and plotting.
- Normalization shall preserve accession/reporting keys to enable traceability from charted points back to filings.
- Tabular schema evolution shall be versioned to prevent downstream pipeline breakage.

### SECAPI-10 Issuer Fundamentals Discovery Utilities

- System shall include issuer-level discovery helpers for enumerating available concepts before selecting metrics.
- Discovery outputs shall expose concept namespaces and concept availability counts for strategy feature engineering.
- Metric selection logic shall account for uneven concept availability across companies and reporting periods.

## 54. Additional Requirements from External Post (Moon Dev, March 9, 2026)

These requirements are derived from the referenced post describing a high-throughput indicator-to-bot research loop.

Observed source links:
- `https://x.com/MoonDevOnYT/status/2030976550360039571?s=20`
- `https://publish.twitter.com/oembed?url=https://x.com/MoonDevOnYT/status/2030976550360039571` (retrieval fallback used to recover post text)
- `https://fxtwitter.com/MoonDevOnYT/status/2030976550360039571` (retrieval fallback used to recover full long-form text)
- `https://t.co/xYK2XsKb2d` (resolves to `https://twitter.com/MoonDevOnYT/status/2030976550360039571/video/1`)

### TVSRC-1 Public Indicator-Script Ingestion Contract

- System shall support ingestion of public community indicator scripts as research candidates with script metadata (source URL, author handle, retrieval timestamp, and revision fingerprint).
- Script ingestion shall enforce license/terms checks and block private or non-permitted sources.
- Candidate registry shall deduplicate scripts by canonical source identifier plus normalized code hash.

### TVSRC-2 Pine-to-Python Translation Pipeline

- System shall support deterministic translation of Pine-style strategy logic into executable Python strategy modules.
- Translation workflow shall persist source script, translated module, and an explicit mapping record for key signal fields to enable audit/debug.
- Translation failures shall be classified and routed to a retry or manual-review queue rather than silently dropped.

### TVSRC-3 Translation Equivalence Validation

- Before promotion, translated strategies shall pass equivalence checks against reference signal behavior on a shared historical sample window.
- Equivalence checks shall validate entry/exit side, threshold comparisons, and position-state transitions with configurable tolerance.
- Strategies failing equivalence validation shall be blocked from downstream optimization and live promotion.

### TVSRC-4 Batch Backtest Factory for Large Candidate Sets

- Research runtime shall support high-throughput batched backtests across many candidate strategies and dataset slices in one orchestrated run.
- Each candidate backtest shall run with isolated paths/config to prevent cross-run artifact contamination.
- Batch scheduler shall capture per-candidate run status so partial failures do not halt unrelated experiments.

### TVSRC-5 Filter-Augmented Variant Expansion and Ablation

- Candidate strategies shall support automatic generation of filtered variants (for example momentum/trend/flow filters) from a baseline signal rule set.
- Evaluation shall include baseline-vs-filtered ablation outputs to quantify whether incremental filters add robust edge.
- Promotion policy shall reject variants whose edge collapses under simple ablation or regime perturbation checks.

### TVSRC-6 Composite-Score Ranking from Results Registry

- System shall maintain a machine-readable results registry (`CSV/JSON`) that ranks strategies by configurable composite score.
- Composite ranking shall include expectancy, profit factor, and risk penalties (drawdown/variance) rather than raw return only.
- Ranking logic shall penalize statistically weak samples (for example low trade count or unstable outliers) to reduce overfit selections.

### TVSRC-7 Short-Side Exit Logic Invariant Tests

- Backtest/execution validation shall include invariant tests for short-side take-profit/stop-loss ordering to prevent max/min inversion bugs.
- Invariant failures shall fail CI/test gates for affected strategy modules.
- Bug-fix revalidations shall be logged with before/after evidence for auditability.

### TVSRC-8 Coverage Pipeline for Trending/Editor-Pick Script Sources

- Candidate discovery shall support scheduled crawling/refresh of trending and editor-pick script lists.
- Discovery runs shall preserve source ranking/context metadata to support later performance attribution by discovery channel.
- Newly discovered scripts shall enter the same standardized translation/backtest/ranking pipeline as existing candidates.

### TVSRC-9 Source Reliability and Claim Handling

- Public claims about extreme performance (for example very high profit factor) shall be marked `unverified` unless reproduced with trade-level artifacts, cost assumptions, and dataset/version provenance.
- Requirements adopted from this source shall focus on reproducible workflow mechanics, not promotional performance claims.

## 55. Additional Requirements from Comparative Platform Assessment (March 10, 2026)

These requirements are derived from a comparative assessment against leading public quant platforms and frameworks focused on casual-user accessibility plus professional depth.

Observed source links:
- `https://www.quantconnect.com/docs/v2/cloud-platform/welcome`
- `https://nautilustrader.io/docs/nightly/`
- `https://www.quantrocket.com/`
- `https://docs.freqtrade.io/en/stable/`
- `https://vectorbt.dev/`
- `https://hummingbot.org/docs/`
- `https://github.com/mementum/backtrader`
- `https://github.com/jakerslam/PQTS/blob/main/pyproject.toml`
- `https://github.com/jakerslam/PQTS/tree/main/results/2026-03-09_sim_suite_baseline`
- `https://github.com/jakerslam/PQTS/tree/main`
- `https://github.com/jakerslam/PQTS/tree/main/src/execution`
- `https://github.com/jakerslam/PQTS/blob/main/docs/QUICKSTART_5_MIN.md`
- `https://github.com/jakerslam/PQTS/blob/main/docs/PRICING_AND_PACKAGING.md`

### COMP-1 Documentation Availability and Metadata Integrity

- Project metadata links (including docs URL from package metadata) shall resolve to live non-404 endpoints.
- CI shall include link-check validation for top-level docs and packaging metadata URLs.
- Release gating shall fail when required public documentation endpoints are unavailable.

### COMP-2 Semantic Release and Distribution Credibility

- Public releases shall follow semantic versioning with changelog entries and GitHub Release artifacts.
- Package distribution workflow shall publish installable artifacts aligned to tagged releases.
- Release metadata shall include commit SHA, build timestamp, and artifact checksums.

### COMP-3 Public Benchmark Quality Gate

- Public reference benchmark bundles shall include execution-quality metrics with explicit acceptance thresholds.
- Publication gate for new reference bundles shall require non-zero fills and reject-rate below configured ceiling for designated reference scenarios.
- If thresholds are not met, bundle publication shall be labeled `diagnostic_only` and excluded from marketing benchmark summaries.

### COMP-4 Golden Dataset and Provenance Governance

- Public benchmark suites shall pin versioned dataset manifests and retain immutable provenance records per run.
- Benchmark comparisons shall require same-dataset comparability checks unless explicitly marked as cross-dataset.
- Changes to benchmark dataset composition shall require version bump and migration note in benchmark docs.

### COMP-5 Reference Strategy Pack Publication Standard

- System shall maintain at least three versioned reference strategy packs with reproducible configs and result artifacts.
- Each reference pack shall include run command, config snapshot, metrics summary, and artifact hashes.
- Reference packs shall be regenerated on schedule and diffed against prior baseline for regression visibility.

### COMP-6 One Engine, Two Product Surfaces

- Architecture shall expose one canonical trading engine through two surfaces: `Studio` (casual-first) and `Core` (professional).
- Studio and Core shall use shared execution/risk/promotion logic and shall not fork strategy semantics.
- Surface-specific UX differences shall be implemented as adapters above common engine APIs.

### COMP-7 Studio (Casual) UX Contract

- Studio onboarding shall be paper-first and support guided setup without manual environment editing on first run.
- Studio shall provide plain-language explanations for trade decisions and risk blocks (`why trade`, `why blocked`).
- Studio shall include template-driven strategy launch and one-click paper campaign execution path.

### COMP-8 Core (Professional) UX Contract

- Core shall expose CLI, notebook, and API interfaces with deterministic replay and full run provenance.
- Core shall include advanced execution analytics (for example TCA/shortfall/reconciliation) and canary promotion controls.
- Core deployment model shall support local and hosted/on-prem parity for critical execution paths.

### COMP-9 Surface Parity and Traceability

- Any action available in Studio shall map to an auditable Core-equivalent command or API call.
- UI workflows shall be able to reveal underlying code/config representation for transparency and reproducibility.
- Event and decision identifiers shall be consistent across surfaces for cross-surface incident debugging.

### COMP-10 Wedge-First Market Scope Governance

- Product roadmap shall define one primary market wedge for initial dominance before multi-market expansion.
- Expansion to additional market classes shall require passing predefined readiness gates in execution quality, reconciliation accuracy, and incident stability.
- Scope governance shall block simultaneous broadening across multiple new market classes without gate approval.

### COMP-11 First-Success CLI Path

- Primary onboarding shall provide a first-success command path (`init`, `demo`, `backtest`, `paper`) with no manual virtualenv steps required in the default flow.
- Default onboarding flow shall succeed with safe local defaults before any broker/exchange credential wiring.
- CLI shall emit actionable next-step guidance after each onboarding command completes.

### COMP-12 Template-First, Code-Optional, Code-Visible Operation

- Strategy workflows shall support template-first operation for new users while preserving full code-level override paths.
- Generated template runs shall persist the exact config/code used so users can transition from GUI/template mode to code mode without loss.
- Any template action that mutates trading behavior shall produce a diffable configuration artifact.

### COMP-13 Public Claim and Evidence Policy

- Product-level performance claims shall require linked reproducible artifacts and benchmark provenance references.
- Claims lacking reproducible evidence shall be tagged `unverified` in external-facing materials and internal docs.
- Benchmark dashboards shall distinguish `reference`, `diagnostic_only`, and `unverified` result classes.

### COMP-14 Tiering Model Safety Baseline

- Packaging model shall include a paper-only community lane and preserve risk/promotion gates across all paid lanes.
- Live-trading enablement in any tier shall require completion of paper-readiness checks and explicit operator acknowledgment.
- Tier capabilities shall be encoded in entitlement policy files rather than ad hoc UI-only gating.

## 56. Additional Requirements from Language and Stack Direction Assessment (March 10, 2026)

These requirements are derived from an architecture/language direction assessment focused on balancing casual-user accessibility and professional depth.

Observed source links:
- `https://raw.githubusercontent.com/jakerslam/PQTS/main/pyproject.toml`
- `https://github.com/jakerslam/PQTS/blob/main/src/dashboard/app.py`
- `https://github.com/jakerslam/PQTS/blob/main/services/api/app.py`
- `https://nautilustrader.io/docs/latest/developer_guide/`
- `https://raw.githubusercontent.com/jakerslam/PQTS/main/docker-compose.yml`
- `https://github.com/jakerslam/PQTS/blob/main/src/execution/microstructure_features.py`

### LANG-1 Python-First, Not Python-Only Architecture Policy

- System shall keep Python as the primary user-facing language for strategy, research, orchestration, and API composition.
- System shall avoid full-platform rewrites into a single native language when user-facing productivity and ecosystem leverage would regress.
- Architecture roadmap shall explicitly reserve native-language modules for performance-critical kernels only.

### LANG-2 Native Kernel Boundary for Hot Path

- Performance-critical execution kernels shall be implemented in a native module boundary (Rust-first target) exposed to Python.
- Native kernel modules shall be packaged as installable Python extensions with reproducible build tooling.
- Native boundary contracts shall be typed and versioned to prevent drift between Python orchestrators and native kernels.

### LANG-3 Native Migration Trigger Criteria

- Migration from Python to native implementation shall require measured trigger evidence (latency/throughput/cost bottleneck) rather than speculative optimization.
- Numeric vectorizable kernels shall be evaluated with JIT acceleration before native rewrite.
- Stateful streaming kernels (orderbook sequencing, replay, deterministic routing/fill engines) shall be prioritized for native migration when trigger thresholds are met.

### LANG-4 Research Data Plane Standard

- Research data plane shall support Arrow-native columnar storage and compute-friendly local formats for reproducible analysis.
- Local-first research workflows shall support Parquet-backed datasets with SQL analytics execution for casual and pro users.
- Data-plane adapters shall preserve schema/version metadata required for benchmark comparability and replay.

### LANG-5 API and Configuration Contract Hardening

- API payloads, strategy manifests, and runtime config surfaces shall be validated through typed schema models rather than ad hoc dict parsing.
- Contract validation errors shall fail fast with actionable diagnostics at boundary ingress.
- Contract schema evolution shall be versioned and compatibility-tested in CI.

### LANG-6 UI Surface Coherence Requirement

- Product shall converge to one primary operator UI architecture per release phase and avoid dual-framework control-plane ambiguity.
- Runtime and deployment manifests shall not launch mismatched UI runtimes against incompatible app entrypoints.
- UI convergence plan shall include explicit deprecation milestones for legacy surfaces with parity gates.

### LANG-7 FastAPI-Centered Control Plane

- Control-plane APIs (health/readiness/auth/session/event routes) shall remain centered on the canonical FastAPI service.
- UI surfaces shall consume a shared API contract rather than bypassing control-plane policy enforcement.
- WebSocket and streaming contracts shall remain consistent across UI clients and automation agents.

### LANG-8 Storage-Tier Policy

- Local/casual analysis workflows shall default to file-backed analytical storage optimized for quick setup and portability.
- Operational state (identity, sessions, entitlements, audit trails, reconciliation metadata) shall remain in transactional stores with explicit schema governance.
- High-volume telemetry-specific stores shall be introduced only when measured workload evidence exceeds current-store thresholds.

### LANG-9 Engine-Loop and Dashboard Responsiveness SLOs

- Runtime shall define explicit cycle-time and UI-refresh SLO targets by mode (research, paper, live) and track them as first-class telemetry.
- Performance claims for execution responsiveness shall reference measured SLO compliance windows.
- Architecture changes intended for latency reduction shall include before/after benchmark evidence.

### LANG-10 Interop Packaging and Distribution

- Native extension modules shall be distributed through standard Python packaging workflows compatible with the project release pipeline.
- Build matrix for native components shall publish platform artifacts required by supported Python versions.
- Release metadata shall include native module build provenance and compatibility information.

### LANG-11 UI Migration Safety

- UI migration (for example legacy dashboard to web app) shall preserve operator-critical workflows and risk controls through parity tests.
- Migration cutover shall be blocked if parity checks fail on key metrics, incident controls, or operator actions.
- Legacy UI retirement shall only occur after staged stabilization windows and documented rollback paths.

### LANG-12 Source Reliability and Claim Handling

- Public stack-performance claims (for example sub-millisecond or “institutional speed”) shall be labeled `unverified` unless backed by reproducible benchmark artifacts.
- Requirements adopted from comparative stack commentary shall emphasize measurable system contracts, not language-brand claims.

## 57. Additional Requirements from Polymarket Official Repo Stack (March 10, 2026)

These requirements are derived from the referenced post and attached Polymarket repository set describing official SDK, CLI, example, and exchange-contract workflows for prediction-market automation.

Observed source links:
- `https://x.com/helicerat0x/status/2031092588648804706?s=20`
- `https://github.com/Polymarket`
- `https://github.com/Polymarket/py-clob-client`
- `https://github.com/Polymarket/rs-clob-client`
- `https://github.com/Polymarket/polymarket-cli`
- `https://github.com/Polymarket/examples`
- `https://github.com/Polymarket/ctf-exchange`
- `https://github.com/Polymarket/ctf-exchange/blob/main/docs/Overview.md`

### PMKT-1 Official Integration Index

- System shall maintain a machine-readable index of officially supported venue SDK/CLI/integration modules, including version, maturity status, and owner.
- Integration index updates shall be validated in CI to prevent stale repository links and broken onboarding references.

### PMKT-2 Auth State Segmentation for Venue Clients

- Venue clients shall implement explicit read-only and authenticated operating states with guardrails that block trading endpoints before authentication.
- Authentication transitions shall emit audit events containing actor, venue, timestamp, and auth method.

### PMKT-3 Signature-Type and Funder Address Contract

- Venue adapters shall support explicit signature-type selection (`eoa`, `proxy`, `safe` or venue-equivalent).
- For delegated/proxy wallet modes, adapter contracts shall require a funder wallet binding and prevent order submission when funder context is unresolved.
- Where deterministic funder derivation is supported by venue rules, adapters shall provide deterministic derivation plus explicit override path.

### PMKT-4 API Credential Lifecycle and Rotation

- Authenticated venue clients shall support create/derive API credential workflows with scoped key usage for trading endpoints.
- Credential rotation and revocation actions shall be exposed through CLI/API and tracked in immutable audit logs.

### PMKT-5 Allowance and Approval Preflight Controls

- Trading adapters for approval-based venues shall run pre-trade allowance checks for required collateral/outcome assets and block orders when approvals are missing.
- System shall provide an explicit approval setup workflow and an approval status check command suitable for automation.
- Approval checks shall distinguish wallet modes that require manual approvals from wallet modes that do not.

### PMKT-6 Canonical Order Lifecycle and Batch Operations

- Order lifecycle shall expose canonical create/sign/post/cancel actions for both market-style and limit-style orders.
- Batch order post/cancel operations shall return per-order success/failure details with stable machine-readable schemas.
- Order time-in-force options supported by venue contracts shall be represented as typed enums in adapters and surfaced in CLI/API.

### PMKT-7 Streaming Coverage and Disconnect Safety

- Venue adapters shall support real-time subscriptions for orderbook, price/midpoint, user orders, and user trades where available.
- Streaming adapters shall implement reconnect/backoff with explicit stream health telemetry and gap-recovery signaling.
- If enabled by policy for a venue, disconnect heartbeats shall trigger protective cancellation of open orders.

### PMKT-8 Remote Signer and Builder-Mode Support

- Authentication layer shall support local signers and remote signer backends (for example KMS/HSM or signing service) behind one signer interface.
- System shall support a promoted builder/institutional auth mode with isolated credentials and explicit scope controls.
- Signing-path latency and failure metrics shall be captured for operational monitoring.

### PMKT-9 CLI Automation Contract

- CLI shall provide both human-readable and machine-readable output modes for all operational commands.
- Machine-readable mode shall emit structured errors with stable schema and non-zero process exits on failures.
- Credential-source precedence (flag, env, config file) shall be deterministic and documented.

### PMKT-10 Read-Only First and Guided Setup UX

- Market discovery, metadata, and read-only analytics commands shall be usable without wallet initialization.
- System shall provide a guided setup path from zero-config state to first authenticated trade in the minimum number of steps.
- Quickstart docs shall include copy-run paths for both read-only and authenticated workflows.

### PMKT-11 Wallet-Mode Example Packs and Smoke Tests

- Repository shall include runnable example packs for each supported wallet mode, including environment-variable templates.
- CI shall execute smoke tests for example packs to detect onboarding drift.
- Example packs shall be versioned alongside adapter contract changes.

### PMKT-12 Hybrid Matching and Non-Custodial Settlement Invariants

- Prediction-market execution model shall support hybrid architecture where matching may occur off-engine/off-chain while settlement remains non-custodial and verifiable.
- Signed order messages shall use typed structured data with domain separation and chain binding equivalent to EIP-712 semantics.
- Settlement logic for complementary outcomes shall support normal fill, mint-cross, and merge-cross matching scenarios with invariant tests.

### PMKT-13 Complementary-Outcome Fee Symmetry

- Fee model for complementary binary outcomes shall enforce economic symmetry between equivalent complementary trades.
- Fee formulas, rounding rules, and inputs shall be versioned and covered by deterministic tests across edge prices.
- Trade-cost analytics shall report fee decomposition to allow verification of symmetry assumptions.

### PMKT-14 Deployment Registry and Audit Artifact Governance

- System shall maintain chain/environment-specific registries of approved settlement contract addresses and versions.
- Live trading startup shall fail closed when configured settlement addresses are not present in approved registries.
- External smart-contract audit artifacts and internal risk-acceptance statuses shall be linked to each approved contract version.

### PMKT-15 Source Reliability and Claim Handling

- Requirements adopted from social-post discovery shall be grounded in repository-documented capabilities and not profitability claims.
- Any performance or profitability claims from social context shall be labeled `unverified` unless reproduced with PQTS benchmark artifacts.

## 58. Additional Requirements from Competitive Moat Assessment (March 10, 2026)

These requirements are derived from a competitive-gap assessment focused on what moves PQTS from parity to durable leadership.

Observed source links:
- `https://www.quantconnect.com/docs/v2/cloud-platform/welcome`
- `https://www.quantconnect.com/docs/v2/writing-algorithms/live-trading/reconciliation`
- `https://nautilustrader.io/docs/latest/concepts/overview/`
- `https://docs.freqtrade.io/en/stable/`
- `https://hummingbot.org/hummingbot-api/`
- `https://www.quantrocket.com/docs/`

### MOAT-1 Per-Order Truth Graph

- System shall persist an end-to-end order truth graph linking research assumptions, signal emission, risk decision, router decision, venue acknowledgment, fill events, and realized attribution.
- Every node and edge in the truth graph shall carry stable identifiers and timestamps for deterministic replay and audit.
- Order-level graph data shall be queryable by strategy, venue, run ID, and incident ID.

### MOAT-2 Live Divergence Diagnosis and Prescriptive Actions

- System shall automatically classify live-vs-expected divergence at order level using a standardized reason taxonomy (for example price drift, liquidity miss, venue reject, latency breach, policy block).
- Divergence outputs shall include prescriptive next actions (`resize`, `reroute`, `hold_canary`, `rollback`) with confidence scores.
- Diagnosis artifacts shall be attached to incident timelines and promotion decisions.

### MOAT-3 Promotion OS State Machine

- Promotion lifecycle shall be implemented as an explicit state machine: `backtest -> paper -> shadow -> canary -> live`.
- State transitions shall be policy-gated and blocked unless required quantitative and risk thresholds pass.
- Transition records shall be signed, immutable, and linked to evidence artifacts used for the decision.

### MOAT-4 Promotion Memo and Rollback Contract

- Each promotion transition shall auto-generate a machine-readable and human-readable promotion memo containing metrics, risk deltas, approval lineage, and capital limits.
- Every transition shall define measurable rollback criteria before activation.
- Rollback execution shall preserve pre-transition state snapshots and emit post-rollback verification artifacts.

### MOAT-5 Stage-Aware Capital Allocation

- Capital allocation policy shall be stage-aware, with explicit exposure envelopes by lifecycle stage and strategy risk tier.
- Automatic capital expansion shall require sustained policy compliance windows; contraction shall trigger immediately on threshold breaches.
- Allocation policy changes shall require auditable approval events.

### MOAT-6 Execution Intelligence Data Model

- System shall continuously collect venue-specific execution intelligence including rejects, slippage, cancel/replace latency, queue behavior, and outage signatures.
- Execution intelligence features shall be versioned and retained for model training and post-trade analytics.
- Missing or degraded telemetry coverage for required features shall trigger quality alerts.

### MOAT-7 Adaptive Routing and Throttling from Execution Intelligence

- Router shall consume execution-intelligence signals to adapt venue selection, order sizing, and throttle behavior.
- Adaptive routing decisions shall remain bounded by explicit risk and policy constraints.
- Routing-policy changes shall be replayable and attributable to model/version IDs.

### MOAT-8 Single Strategy Object Across Casual and Pro Surfaces

- Studio templates and Core code workflows shall map to one canonical strategy object and one canonical config contract.
- Any UI mutation shall produce a diffable config/code artifact that can be executed identically via CLI/API.
- Strategy promotion history shall remain continuous when moving from guided mode to professional mode.

### MOAT-9 Bidirectional Transparency and Parity

- UI actions shall reveal equivalent CLI/API commands and config deltas.
- CLI/API changes shall be visible in UI without semantic drift.
- Cross-surface parity tests shall fail release gates when behavior diverges for equivalent actions.

### MOAT-10 Policy-Constrained Autonomous Operator

- Autonomous operator capabilities shall be split into `propose`, `simulate`, and `execute` permissions with least-privilege enforcement.
- Execute permissions for capital-impacting actions shall require policy checks and approval workflows.
- All operator actions and blocked actions shall be logged with rationale and policy references.

### MOAT-11 Incident Co-Pilot and Safe Rollback Assist

- Incident assistant workflows shall produce structured incident classifications, candidate mitigations, and rollback plans based on truth-graph evidence.
- Automated mitigations shall be limited to policy-approved safe actions; higher-risk actions require human approval.
- Post-incident reports shall include action timelines, evidence links, and prevention follow-ups.

### MOAT-12 Proof-as-Product Artifact Pipeline

- System shall publish scheduled benchmark bundles, drift reports, venue certification status, and incident postmortems as first-class product artifacts.
- Published artifacts shall include reproducible commands, dataset/version provenance, and machine-readable metric manifests.
- Artifact publication shall be blocked when required provenance or evidence fields are missing.

### MOAT-13 Public Trust Classifications and Evidence Gates

- Public-facing metrics shall be classified as `verified`, `diagnostic_only`, or `unverified` with explicit definitions.
- Any claim without required reproducible evidence shall be automatically downgraded to `unverified`.
- Trust classification policy shall be enforced in CI for docs, reports, and benchmark pages.

### MOAT-14 Team Governance and Capital Controls

- Team workflows shall include review/approve/promote/kill actions with role-based controls and immutable audit trails.
- Per-strategy and per-venue capital envelopes shall be enforced by policy engine with emergency override governance.
- Governance controls shall support separation-of-duties constraints for model authoring, approval, and live activation.

### MOAT-15 Moat-vs-Parity Roadmap Governance

- Roadmap items shall be tagged `parity` or `moat` with explicit expected advantage horizon.
- Capacity planning shall enforce a configurable minimum delivery share for moat work after parity baseline gates are satisfied.
- Quarterly reviews shall evaluate moat efficacy using adoption, retention, incident reduction, and execution-quality deltas.

### MOAT-16 Source Reliability and Claim Handling

- Requirements adopted from comparative commentary shall encode measurable system contracts and not rely on vendor marketing claims.
- Competitive feature references shall be periodically revalidated against current public documentation before roadmap commitments.

## 59. Additional Requirements from External Repo (Nunchi agent-cli, March 10, 2026)

These requirements are derived from features observed in `Nunchi-trade/agent-cli` and adapted to PQTS architecture/safety constraints.

Observed source links:
- `https://github.com/Nunchi-trade/agent-cli`
- `https://github.com/Nunchi-trade/agent-cli/blob/main/README.md`
- `https://github.com/Nunchi-trade/agent-cli/blob/main/docs/api-reference.md`

### NCLI-1 Authenticated SSE Stream Surface

- API layer shall expose authenticated Server-Sent Event channels for `orders`, `fills`, `positions`, `pnl`, and `risk`.
- SSE channels shall include correlation IDs, account-scoped filtering, and heartbeat events for resilient dashboard/integration consumers.
- SSE transport shall coexist with existing websocket channels and share canonical event envelope contracts.

### NCLI-2 Skill Package Discovery and Distribution Contract

- System shall support workflow skills as local `skills/<name>/SKILL.md` packages discoverable via CLI.
- CLI shall provide deterministic skill discovery output and machine-readable modes.
- CLI shall emit raw URL distribution links for skill packages to support agent-install workflows.

### NCLI-3 Nightly Bounded Self-Improvement Review Loop

- System shall provide a nightly review runner over latest paper campaign snapshots to evaluate reject-rate, slippage quality, realized net alpha, and critical alerts.
- Review engine shall generate bounded, reversible parameter-adjustment proposals with explicit before/after deltas.
- Auto-apply mode shall require explicit operator confirmation and preserve pre-change config backups.

### NCLI-4 Deployment Run-Mode Contract

- Deployment entrypoints shall support explicit run modes (for example `engine`, `api`, `stream`) via environment variables without editing code.
- Each run mode shall have declared required environment variables and health/readiness behavior.
- Runtime shall fail closed with explicit diagnostics when run-mode prerequisites are missing.

### NCLI-5 Agent Memory/Journal/Judge Artifact Contract

- System shall standardize operator-facing memory, trade-journal, and judgment-report artifacts for autonomous loops.
- Artifacts shall be timestamped, versioned, and linked to strategy/run identifiers for auditability.
- Promotion and incident workflows shall reference these artifacts when generating operator recommendations.

### NCLI-6 Source Reliability and Claim Handling

- External strategy/runtime claims from repository marketing copy shall be treated as design hypotheses until reproduced under PQTS benchmarks.
- Imported requirements from this source shall be encoded as testable system contracts rather than profitability assertions.

## 60. Additional Requirements from PQTS State/Trust-Surface Review (March 10, 2026)

These requirements are derived from a repository-state review emphasizing noob/pro usability, trust-surface consistency, benchmark depth, and verified ecosystem coverage.

Observed source links:
- `https://github.com/jakerslam/pqts`
- `https://raw.githubusercontent.com/jakerslam/pqts/main/docs/QUICKSTART_5_MIN.md`
- `https://raw.githubusercontent.com/jakerslam/pqts/main/docs/IMPLEMENTATION_DIRECTION.md`
- `https://raw.githubusercontent.com/jakerslam/pqts/main/results/native_benchmarks/README.md`
- `https://raw.githubusercontent.com/jakerslam/pqts/main/src/dashboard/start.py`
- `https://raw.githubusercontent.com/jakerslam/pqts/main/docs/BENCHMARKS.md`
- `https://raw.githubusercontent.com/jakerslam/pqts/main/docs/ISSUE_BACKLOG.md`
- `https://raw.githubusercontent.com/jakerslam/pqts/main/docs/USER_RESEARCH_2026_03.md`

### COMP-15 Distribution and Install-Path Truth Consistency

- Public install instructions shall remain synchronized with real distribution availability (for example PyPI package existence and version availability).
- If a package/distribution channel is unavailable, user-facing docs/README/quickstart shall automatically downgrade to a source-install path and label package install as unavailable.
- Release gates shall fail when install claims in docs conflict with runtime package registry status for the tagged version.

### COMP-16 Version and Maturity Posture Consistency Gate

- Repository docs shall use one canonical released version and maturity posture (`alpha`, `beta`, `stable`) per release line.
- Stale version claims (for example non-existent major/minor release numbers) or maturity contradictions (`production-ready` vs `alpha`) shall fail docs validation gates.
- Changelog, README, quickstart, and packaging metadata shall be checked for consistency before release publication.

### LANG-13 Dashboard Runtime Safety and Port Consistency

- Dashboard runtime entrypoints shall expose one canonical default port per surface and prohibit conflicting defaults across launch scripts and docs.
- Production launch paths shall disable debug-mode server settings by default and require explicit opt-in for local development debug mode.
- External stylesheet/script dependencies in operator-critical dashboards shall be pinned or mirrored to controlled assets for deterministic behavior and security review.

### COMP-17 Benchmark Program Coverage and Cadence

- Public benchmark publication shall operate as a matrix program across strategy class, market class, venue, and time window rather than isolated single bundles.
- Benchmark reports shall include paper/live drift diagnostics and execution-quality metrics (fill, reject, slippage/TCA, and incident-rate context) for each matrix segment.
- Monthly benchmark publication shall include trend deltas vs prior month with machine-readable summaries suitable for independent reproduction.

### PMKT-16 Marketing-to-Verified Integration Parity Gate

- Marketing claims about supported venues/market classes shall be validated against the machine-readable official integrations index before release.
- Any claimed venue lacking verified adapter status in the canonical index shall be labeled `planned` or removed from primary marketing claims.
- CI shall fail when integration coverage claims in README/docs drift from canonical integration metadata.

### LANG-14 Public Surface Canonicalization Contract

- Public-facing onboarding shall identify exactly one primary web surface for the active release phase and clearly label secondary surfaces as internal/legacy/transition.
- Runtime launch docs and compose profiles shall prioritize the primary surface and avoid presenting overlapping equivalent paths without migration context.
- Surface-transition plans shall publish explicit cutover criteria and rollback criteria tied to parity and reliability checks.

### COMP-18 External User-Validation Evidence Contract

- Beginner/pro usability claims shall be supported by externally sourced cohort evidence, not internal proxy runs only.
- User-research artifacts shall record cohort provenance (external vs internal), cohort size, task success rates, and top blockers per persona.
- Public readiness claims for noob/pro friendliness shall require at least one external cohort cycle in the current release window.

## 61. Additional Requirements from Recogard Post + Gabagool Polymarket Bot Repo (March 10, 2026)

These requirements capture additive, applicable strengths from the referenced X post and linked repository while preserving PQTS safety/truth-surface constraints.

Observed source links:
- `https://x.com/recogard/status/2031145282944045293?s=46`
- `https://api.fxtwitter.com/recogard/status/2031145282944045293`
- `https://github.com/Gabagool2-2/polymarket-trading-bot-python`
- `https://raw.githubusercontent.com/Gabagool2-2/polymarket-trading-bot-python/main/README.md`

### RCG-1 Time-Bucket Market Discovery and Asset Resolution

- System shall support deterministic discovery of recurring short-horizon markets by configured time-bucket templates (for example `5m` epoch windows).
- Before signal or execution, system shall resolve and validate venue market identifiers required for trading (for example market/condition IDs and YES/NO asset IDs).
- If discovery returns zero matches, multiple ambiguous matches, or incomplete identifiers, strategy shall fail closed and emit explicit diagnostics.

### RCG-2 Live-Market Dry-Run Parity Mode

- Dry-run mode shall use the same live market-data, signal, and decision pipeline as live mode.
- In dry-run mode, order submission shall be replaced with deterministic simulated fills using configurable top-of-book, latency, and slippage assumptions.
- Dry-run artifacts shall include per-order `would_submit`, `would_fill`, and `why_blocked` outputs for promotion/readiness review.

### RCG-3 Complementary Bundle Edge Gate with Fee Realism

- Complementary YES/NO bundle opportunities shall require edge checks using modeled order-style fees and slippage (`maker`/`taker` aware), not fee-free assumptions.
- Strategy shall block execution when apparent bundle edge disappears after modeled fees, slippage, and residual risk buffers.
- Execution diagnostics shall log pre-fee edge, post-fee edge, and selected order-style assumptions per opportunity.

### RCG-4 Dynamic Limit-Order Repricing Controller

- Short-cycle strategies shall support cancel/replace repricing for active limit orders based on orderbook movement and stale-quote thresholds.
- Repricing controls shall enforce bounded cancel/replace rates, max unfilled dwell time, and legging-risk protections.
- Runtime telemetry shall track cancel/replace intensity, quote lifetime, and repricing effectiveness for each strategy/venue pair.

### RCG-5 Maker-First Order-Style Policy

- Strategy templates shall support maker-first (`post_only`) execution with explicit taker fallback policy.
- Taker fallback shall only be allowed when net EV remains positive after taker fees and latency-impact assumptions.
- Per-order records shall capture order-style selection rationale (`maker`, `taker_fallback`, `blocked`).

### RCG-6 Resolution-to-Redeem Automation Lifecycle

- System shall include a settlement worker that detects claimable resolved positions and executes redeem/claim operations automatically when enabled.
- Redeem flow shall be idempotent with retry/backoff controls and fail-closed behavior on uncertain resolution state.
- Telemetry shall include redeem attempts, success/failure reasons, settlement lag, and redeemed notional/PnL attribution.

### RCG-7 Multi-Source Reference Price and Strike Context

- Short-cycle signal engines shall support multiple reference-price providers with source-priority and freshness rules.
- Optional strike/context scrapers may be used only when provenance, timestamp freshness, and schema validation checks pass.
- Large cross-source divergence shall downgrade signal confidence or block entries according to configurable thresholds.

### RCG-8 Progressive Stepwise Beginner Validation Ladder

- Repository shall provide numbered validation steps from configuration -> market discovery -> stream health -> signal generation -> dry-run execution.
- Each step shall emit machine-readable pass/fail output and remediation hints.
- Quickstart docs shall link this stepwise ladder and the full-cycle command path for first-success onboarding.

## 62. Additional Requirements for Greatly Upgraded Unified UI (March 10, 2026)

These requirements codify a web-primary UI that serves beginners and professionals on one canonical product surface.

Observed source links:
- `https://github.com/jakerslam/pqts/blob/main/docs/IMPLEMENTATION_DIRECTION.md`
- `https://github.com/jakerslam/pqts/blob/main/src/dashboard/app.py`
- `https://github.com/jakerslam/pqts/blob/main/docs/ISSUE_BACKLOG.md`
- `https://github.com/jakerslam/pqts/blob/main/docs/QUICKSTART_5_MIN.md`

### UI-001 One Primary Surface Contract

- Web app shall be the primary external UI surface.
- Legacy dashboard surfaces shall be explicitly marked transitional/operator-only until parity gates pass.
- System documentation shall expose one canonical user-facing navigation model and URL hierarchy.

### UI-002 Unified Product Model Across User Densities

- UI shall provide Guided and Pro density modes on the same underlying domain objects (accounts, runs, orders, fills, incidents, artifacts).
- Guided mode shall reduce cognitive load and provide contextual explanations.
- Pro mode shall expose raw fields, traces, venue details, and advanced controls.
- Product architecture shall not fork into separate beginner/professional applications.

### UI-003 Global Trust and Runtime Status Bar

- Every page shall expose a global trust/status bar containing at minimum:
  - environment (`demo`, `paper`, `shadow`, `canary`, `live`),
  - workspace/account/venue context,
  - connectivity and data freshness,
  - native hotpath status (`native` or `fallback`),
  - kill-switch state,
  - run/trace ID,
  - trust/provenance label for active data.

### UI-004 Browser-First Safe Onboarding

- Browser onboarding shall support demo exploration, template backtest, and bounded paper-campaign start without CLI dependency.
- Default onboarding shall fail closed for live execution and shall not require live credentials.
- Default onboarding shall not expose unsafe hidden auto-execution behavior.

### UI-005 Time-to-Meaningful-Result SLO

- Median time to first meaningful result on clean setup shall be under five minutes.
- Meaningful result shall require completion of demo/backtest/paper artifact generation with visible outcome, explanation, and next-step guidance.

### UI-006 GUI-to-Code Transparency Contract

- Any action that changes strategy behavior shall expose generated config, CLI/code equivalent, config diff, and output artifacts.
- UI shall preserve CLI/API parity so advanced users can bypass UI without loss of functionality.

### UI-007 Primary Navigation Information Architecture

- Primary navigation shall include Home, Strategy Lab, Portfolio, Execution, Risk, Promotions, Benchmarks/Results, Alerts, and Settings/Integrations.
- Navigation and route naming shall remain stable across Guided and Pro modes.

### UI-008 Command Center Landing Contract

- Home/Command Center shall answer above-the-fold:
  - what is running now,
  - current safety posture,
  - health status,
  - capital performance,
  - highest-priority operator action.
- Command Center shall include portfolio summary, today PnL, open exposure, active incidents, current promotion stage, benchmark/reference callout, latest provenance marker, and one-click next action.

### UI-009 Empty-State Integrity

- Empty, unavailable, disconnected, and stale-data states shall be explicit and visually distinct from healthy trading states.
- Empty states shall include guided next actions for first-time users.
- Production UI shall never present silent zeros as success states when data is unavailable.

### UI-010 Guided Strategy Lab

- Strategy Lab shall provide template gallery flows with plain-language explanation of behavior, suitable market conditions, key risks, and success metrics.
- Parameter editing shall default to safe constraints with human-readable labels.
- Advanced parameters shall be progressively disclosed, not removed.

### UI-011 Metric Explainability

- Major KPIs shall expose plain-language meaning, metric definition/formula, importance rationale, threshold interpretation, and link to underlying raw data.
- KPI explainability shall cover at minimum Sharpe, drawdown, fill rate, reject rate, slippage, canary readiness, and optimization priority.

### UI-012 Safe Capital-Affecting Action Patterns

- Paper-first progression shall be default.
- Promotion-capable actions shall display current stage, gate status, unmet checks, rollback criteria, and risk impact before confirmation.
- Capital-affecting and destructive actions shall require explicit confirmation and audit logging.

### UI-013 Portfolio Surface Requirements

- Portfolio view shall provide positions, balances, allocations, realized/unrealized PnL, and filters by account/venue/strategy/time.
- Portfolio cards shall drill through to order/fill-level details.
- Data views shall support export and cross-strategy/cross-venue comparison.

### UI-014 Execution Surface Requirements

- Execution view shall provide live order/fill tape, order lifecycle timelines, reject reasons, cancel/replace reasons, venue acknowledgments, latency, and slippage views.
- Per-order explainability shall link strategy decision -> risk gate -> router decision -> venue response -> fill outcome.

### UI-015 Risk and Incident Surface Requirements

- Risk/Incident view shall provide current limits/utilization, kill-switch state, incident timeline, impacted scope, recommended next actions, and audited operator actions.
- Role-gated controls shall include pause, flatten, reduce, and kill.

### UI-016 Promotion Lifecycle Surface Requirements

- Promotion UI shall model full stage progression: `backtest -> paper -> shadow -> canary -> live`.
- Each stage shall expose gate checklist, evidence bundle, benchmark comparison, trust label, approver/audit trail, rollback plan, and blockers.

### UI-017 Artifact Provenance Visibility

- Every run, chart, benchmark card, and recommendation shall expose trust label, generation timestamp, run/trace ID, config version, code version/commit, data source, environment, and initiator identity.

### UI-018 Benchmarks Above the Fold

- Benchmark/reference callouts shall be visible on Command Center and Strategy surfaces.
- UI shall clearly separate `reference` results from diagnostic and experimental artifacts.

### UI-019 WebSocket-First Live UX

- Live execution/risk/PnL/incident views shall be stream-first.
- Polling may exist as fallback only.
- Stream status shall be explicit (`connected`, `degraded`, `reconnecting`, `stale`).

### UI-020 No Silent Demo Data on Production Surfaces

- Production surfaces shall not silently substitute demo/synthetic data when real data is missing.
- When data is absent, UI shall show explicit unavailable/disconnected states with remediation hints.

### UI-021 Graceful Degradation and Loud Failure

- Stream degradation states shall show staleness indicator, reconnect status, last successful timestamp, and degraded-capability warning.
- Risk/incident alert rendering failures shall fail loudly and be observable.

### UI-022 Tokenized Design System Requirement

- UI shall replace ad hoc styling and unmanaged external stylesheet dependence with a tokenized design system.
- Design tokens shall cover color, typography, spacing, motion, density, radii, and shadow semantics.
- Status colors shall be semantic and consistent for gain/loss, pass/hold/fail, connected/degraded/down, and paper/live.

### UI-023 Accessibility Contract

- Core flows shall meet WCAG 2.2 AA.
- Keyboard navigation shall cover all primary actions.
- Tables/charts shall include accessible labels and text equivalents.
- Color-only status communication shall be prohibited.

### UI-024 Dense but Controllable Data Presentation

- Data tables shall support sorting, filtering, resizing, pinning, and virtualization.
- Charts shall support annotations, reference overlays, and deep-links to underlying records.
- Users shall be able to switch between compact and expanded density modes.

### UI-025 Global Search and Command Palette

- Global search shall index strategies, orders, fills, incidents, accounts, runs, and relevant documents.
- Command palette shall expose high-frequency operator actions and navigation commands.
- Keyboard-first operation shall be supported for power users.

### UI-026 Auth-Aware Shell and Role Visibility

- Shell shall adapt navigation and capabilities by role and environment.
- Viewer, operator, and admin roles shall have distinct visibility/action rights.
- Sensitive credentials and high-risk controls shall remain masked or inaccessible by default.

### UI-027 Privileged Action Audit Contract

- Any pause/flatten/risk-override/promotion action shall record actor, role, timestamp, target, reason, before/after state, and trace ID.

### UI-028 Assistant as Additive Surface

- Assistant/chat shall augment but not replace core execution/risk/product navigation.
- Assistant results shall render as typed widgets when contracts exist, with safe fallback rendering otherwise.
- Assistant outcomes shall resolve to concrete pages, artifacts, diffs, or draft actions.

### UI-029 Constrained Assistant Action Policy

- Assistant shall be limited to recommend/draft/summarize/explain unless user approval and role/policy gates permit execution.
- Capital-affecting actions initiated via assistant shall pass the same confirmation, role, and audit controls as manual actions.

### UI-030 UI Product Analytics Contract

- Product analytics shall capture time-to-first-meaningful-result, onboarding drop-off, time-to-first-paper-campaign, time-to-reject-reason diagnosis, time-to-incident-triage, Guided-vs-Pro usage split, and trust-label comprehension interactions.

### UI-031 UI SLO Contract

- Core page p95 interactive time shall be under two seconds.
- Live-tape/incident rows shall target p95 stream-to-visible update under 500ms.
- Risk/incident rendering shall have zero silent-failure tolerance.
- Stream interruptions shall provide recoverable reconnect paths.

## 63. Acceptance Criteria for Greatly Improved UI v1

- Brand-new users shall complete demo -> backtest -> bounded paper flow from UI without CLI dependency or unsafe prompts.
- Median time to first meaningful output shall be under five minutes.
- Professional users shall identify order reject reason within 30 seconds and within three clicks from execution surface.
- All live/canary pages shall expose environment, data freshness, hotpath/fallback status, and kill-switch state without scrolling.
- Every benchmark/result artifact shall expose trust label and provenance in one interaction.
- Production pages shall not silently substitute demo data.
- Portfolio, execution, and risk pages shall consume canonical API/stream contracts rather than bespoke page-local adapters.
- Legacy public UI surface shall not be deprecated until critical-workflow parity gates are demonstrated.

## 64. Coherence and Truth-Surface Closure Requirements

These requirements codify external review findings focused on eliminating control-plane drift and contradictory public narratives.

### COH-1 Web Client Contract Coherence

- Web API client shall consume canonical FastAPI `/v1` contracts for account, portfolio, execution, and risk resources.
- Deprecated pseudo-contract paths (for example `/api/v1/account`, `/api/v1/orders`) shall not be used for core dashboard reads.

### COH-2 Web Thin-Client Boundary

- Next.js API route handlers for operator and analytics surfaces shall not maintain authoritative in-memory domain state.
- Domain writes/reads (promotion state, operator actions, execution/risk evidence) shall resolve through canonical backend services.

### COH-3 Runtime Command Boundary

- Production web route handlers shall not spawn Python processes for canonical control-plane actions where equivalent backend APIs exist.
- Any temporary command-exec route shall be explicitly marked transitional and removed by cutover gate.

### COH-4 Version Source-of-Truth Consistency

- API-reported service version shall be derived from canonical release metadata (package/project version) unless explicitly overridden.
- Public docs, release references, and runtime banners shall not present conflicting active versions.

### COH-5 Onboarding Path Canonicalization

- README and quickstart shall define one preferred first-success path and one clearly-labeled source/development fallback path.
- Parallel equivalent “first path” narratives that differ in command surface shall be prohibited.

### COH-6 Public Claim Scope Alignment

- Market-scope claims shall align with active strategic wedge and integration maturity states.
- Assets marked experimental in canonical integration index shall not be represented as fully production-certified without explicit qualifier.

### COH-7 Backlog Freshness Contract

- Historical issue-template documents shall be explicitly labeled non-canonical when active backlog state is managed elsewhere.
- Canonical active backlog shall be singular and referenced from all auxiliary backlog documents.

### COH-8 Docs Reachability Fallback

- When GitHub Pages deployment is unavailable due repository permissions, docs publish workflow shall still emit a browsable static artifact.
- README/docs shall document fallback artifact access until primary docs hosting is enabled.

## 65. Competitor Strength Assimilation Requirements (March 11, 2026)

These are gap-oriented requirements extracted from public competitor repository/docs strengths and normalized into PQTS contracts.

Observed source links:
- `https://github.com/freqtrade/freqtrade`
- `https://github.com/nautechsystems/nautilus_trader`
- `https://github.com/hummingbot/hummingbot`
- `https://github.com/QuantConnect/Lean`
- `https://github.com/polakowo/vectorbt`
- `https://github.com/mementum/backtrader`

### LEAN-1 Algorithm Framework Layer Contract

- PQTS shall expose explicit strategy framework interfaces for `alpha`, `universe_selection`, `portfolio_construction`, `execution_model`, and `risk_model`.
- Stage promotion and runtime composition shall accept interchangeable implementations per layer without modifying core engine code.

### LEAN-2 Research-to-Production Template Contract

- PQTS shall ship canonical research templates that map notebook research outputs to production strategy modules with zero manual field remapping.
- Template artifacts shall include data assumptions, feature lineage, and deployable strategy config.

### LEAN-3 CLI Surface Completeness Contract

- PQTS CLI shall expose first-class commands for `project-init`, `research`, `backtest`, `optimize`, and `live` with consistent flags and artifact outputs.
- Command contracts shall remain parity-safe across local and containerized execution paths.

### LEAN-4 Optimization Job Contract

- PQTS shall provide optimization job specifications with reproducible parameter-space definitions, run metadata, and best-result promotion candidates.
- Optimization results shall be serializable and resumable.

### LEAN-5 Data Tooling and Conversion Contract

- PQTS shall provide a toolbox-style data conversion/import layer for external vendor formats with schema validation and reproducible conversion manifests.
- Converted datasets shall emit provenance metadata and checksum artifacts.

### LEAN-6 Brokerage/Data Adapter Readiness Matrix

- PQTS shall maintain machine-readable adapter readiness metadata (capabilities, known limits, maturity state, last validation date) for each venue/provider.
- Public claims shall be constrained to readiness entries marked production-certified.

### FTR-1 Pairlist Pipeline Contract

- PQTS shall implement chainable universe/pairlist handlers with deterministic ordering, refresh cadence controls, and cache policy.
- Handler chain shall support static, liquidity/volume, remote, and producer-fed list sources plus post-filters (spread, volatility, age/delist, precision).

### FTR-2 Strategy Protection Stack Contract

- PQTS shall provide configurable strategy protections including cooldown locks, stoploss-cluster guards, drawdown guards, and low-profit pair locks.
- Protections shall be stage-aware and emit explicit lock/unlock reason codes.

### FTR-3 Lookahead-Bias Detection Contract

- PQTS shall provide a lookahead-bias analysis command that compares baseline and sliced signal runs to detect future-data leakage.
- Output shall include per-strategy bias status, affected indicators/signals, and reproducible evidence artifacts.

### FTR-4 Recursive-Indicator Stability Contract

- PQTS shall provide recursive analysis tooling that evaluates indicator stability across startup-window variants and reports variance risk.
- Strategy promotion gates shall fail when recursive instability exceeds configured thresholds.

### FTR-5 Backtest Artifact Bundle Contract

- PQTS backtests shall export bundled artifacts including metrics, trade log, config snapshot, strategy snapshot, notes, and reproducibility metadata.
- Bundle format shall support UI/CLI reload for subsequent analysis without rerun.

### FTR-6 Producer-Consumer Signal Distribution Contract

- PQTS shall support producer/consumer mode for sharing analyzed frames/signals across bot instances via authenticated stream channels.
- Consumer instances shall verify source freshness and schema before accepting upstream data.

### FTR-7 Operator API + Message Stream Contract

- PQTS shall expose authenticated REST endpoints plus a message websocket/SSE stream for operator actions, bot status, and strategy telemetry.
- API shall support OpenAPI schema export and token-based authentication flows.

### FTR-8 Notification Command Surface Contract

- PQTS shall provide granular operator notification channels with configurable verbosity for strategy, protection, execution, and incident events.
- Notification controls shall be policy-bound and auditable.

### FTR-9 Feature/Target Namespace Contract for ML

- PQTS ML pipelines shall enforce explicit feature and target namespaces with typed validation and confidence/outlier flags returned to strategy logic.
- Live inference trust flags shall be visible in UI and promotion gates.

### NAUT-1 Shared-Core Environment Context Contract

- PQTS shall enforce a shared runtime core across `backtest`, `sandbox`, and `live` contexts with no duplicate business logic implementations.
- Any context-specific divergence shall be declared via explicit adapter/policy boundaries.

### NAUT-2 Deterministic Event Runtime Contract

- PQTS shall preserve deterministic event ordering for core strategy/risk/execution flows under identical inputs and seeds.
- Runtime shall emit deterministic replay hashes for verification.

### NAUT-3 Timestamp Precision Contract

- PQTS shall standardize high-precision UTC timestamp handling across ingest, execution, storage, and replay boundaries.
- Timestamp formatting and precision policy shall be explicit and test-gated.

### NAUT-4 Adapter Triad Contract

- Each venue adapter shall implement a standard triad: instrument provider, data client(s), and execution client(s).
- Adapter contracts shall include reconciliation responsibilities and failure semantics.

### NAUT-5 Backtest Fill-Model Realism Contract

- PQTS shall support data-type-aware fill modeling (bar/L1/L2/L3) with explicit assumptions and immutable historical data policy.
- Fill-model configuration shall expose realism-vs-speed tradeoffs and be reproducible.

### NAUT-6 Live Reconciliation Invariant Contract

- PQTS shall support startup and continuous reconciliation with invariant checks across order/position state and venue reports.
- Reconciliation outcomes shall generate machine-readable discrepancy classes and remediation actions.

### NAUT-7 Component Lifecycle State-Machine Contract

- Core runtime components shall use explicit lifecycle states with guarded transitions and bounded transitional durations.
- Invalid transitions shall fail closed and emit typed diagnostics.

### NAUT-8 Message Bus Externalization Contract

- PQTS shall support internal message bus externalization with type filters, stream routing, and producer/consumer bridge semantics.
- Stream serialization and schema compatibility shall be versioned.

### HBOT-1 Controller/Executor Strategy Architecture Contract

- PQTS shall support controller/executor decomposition for strategy_v2-style composition where high-level controllers orchestrate reusable execution units.
- Executor orchestrator shall manage executor lifecycle, state, and telemetry.

### HBOT-2 Reusable Executor Library Contract

- PQTS shall provide reusable executor modules for common execution intents (for example TWAP, grid, DCA, arbitrage, market-making variants).
- Executors shall have typed configs and deterministic simulation adapters.

### HBOT-3 Collateral-Aware Budget Checking Contract

- PQTS shall provide pre-trade budget checking that can resize or reject order candidates based on available collateral and fee requirements.
- Budget checks shall support all-or-none and partial-resize modes with audit output.

### HBOT-4 In-Flight/Lost-Order Tracking Contract

- PQTS shall maintain robust in-flight order tracking with cached-order retention, lost-order thresholds, and duplicate-safe update handling.
- Lost-order transitions shall be observable and reconciled explicitly.

### HBOT-5 Connector Metrics Collection Contract

- PQTS connectors shall emit standardized connector-level metrics (fills, volume, latency, failures, disconnects) via collector modules.
- Metrics shall be consumable by ops dashboards and promotion gates.

### HBOT-6 Gateway Connector Boundary Contract

- PQTS shall define a gateway boundary for DEX/non-CEX connectivity with clear capability declarations and risk constraints.
- Gateway adapters shall be tested with the same contract suite as direct connectors.

### VBT-1 Vectorized Research Engine Contract

- PQTS research layer shall support vectorized simulation over multi-asset, multi-parameter, multi-period grids using efficient array backends.
- Grid expansion logic shall remain reproducible and memory-bounded.

### VBT-2 Indicator and Signal Factory Contract

- PQTS shall provide indicator/signal factory primitives to generate compiled custom indicators/signals from user functions with typed parameter spaces.
- Factory outputs shall be compatible with backtest and paper/live strategy pipelines.

### VBT-3 Records and Simulation-Log Data Structure Contract

- PQTS shall provide optimized record structures for large simulation logs, fills, and event traces with fast query/reduction primitives.
- Record structures shall support export to analytics-friendly formats.

### VBT-4 Stats and Plot Builder Contract

- PQTS shall expose composable stats and plot builder APIs for strategy, signal, and portfolio components.
- Built stats/plots shall be reusable in UI reports and notebook workflows.

### VBT-5 Persistence Contract for Research Objects

- PQTS shall support persistence and reload of research objects (data snapshots, indicators, portfolio simulations) with schema/version tagging.
- Reloaded artifacts shall preserve deterministic summary metrics.

### BTR-1 Analyzer/Observer/Sizer Plugin Contract

- PQTS shall define first-class plugin contracts for analyzers, observers, and sizers with stable lifecycle hooks and typed outputs.
- Plugin execution shall be deterministic and stage-aware.

### BTR-2 Replay/Resample Synchronization Contract

- PQTS shall provide robust resample/replay pipelines with synchronization invariants across mixed timeframe feeds.
- Replay/resample behavior shall be regression-tested for live/paper/backtest consistency.

### BTR-3 Broker Simulation Order-Semantics Contract

- PQTS broker simulation shall support rich order semantics (market/limit/stop/trailing/bracket/OCO) with configurable commission/slippage/fill policies.
- Simulation order semantics shall map to live adapter capabilities with explicit mismatch warnings.

### BTR-4 Multi-Data Multi-Strategy Orchestration Contract

- PQTS shall support multi-data and multi-strategy orchestration in one runtime with deterministic scheduling and isolated strategy accounting.
- Step-by-step execution mode shall be available for debugging and training workflows.

### BTR-5 Store Pattern Contract for Live Integrations

- PQTS live integrations shall support a store-style abstraction that unifies feed/broker/adaptor state and notifications.
- Store abstractions shall support replayable startup state restoration.

### XCOMP-1 Integration Maturity and Certification Transparency

- PQTS shall expose integration maturity states (`stable`, `beta`, `experimental`, `planned`) with objective promotion criteria and latest certification evidence.
- Marketing/docs/UI shall consume this same canonical maturity registry.

### XCOMP-2 Strategy Template and Example Density Contract

- PQTS shall maintain a high-density library of runnable strategy examples/templates spanning core styles and markets, each with reproducible artifacts.
- Templates shall include beginner and pro variants on the same underlying strategy objects.

### XCOMP-3 Parity-Gated Claim Discipline Contract

- For every externally claimed capability, PQTS shall maintain an automated proof gate (test, artifact, or validation report) before publication.
- Capabilities without current proof shall be labeled clearly as experimental/unverified.

## 66. X Post Assimilation Requirements (gipppezkv, March 10, 2026)

These requirements are distilled from the referenced X post and links, normalized into auditable system contracts.

Observed source links:
- `https://x.com/gipppezkv/status/2031258926461673664?s=20`
- `https://kreo.app/@gipp00` (transaction tracking link referenced in post)
- `https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf` (quoted link in thread context)

### GIPP-1 Probability Edge Modeling Contract

- PQTS shall compute explicit model-vs-market edge per candidate trade as `edge = p_model - p_market`.
- `p_market` derivation shall be reproducible from venue odds/price inputs and stored with each decision.

### GIPP-2 EV-Gated Trade Admission Contract

- PQTS shall require positive cost-adjusted expected value before route submission using a documented formula contract.
- EV calculation inputs (`p_model`, payout/odds transform, fees/slippage assumptions) shall be persisted per decision trace.

### GIPP-3 Fractional Kelly Sizing Contract

- PQTS shall support Kelly-derived sizing with mandatory fractional scaling and hard caps by strategy/stage/account.
- Kelly sizing shall fail closed when probability confidence, liquidity, or model-quality thresholds are not met.

### GIPP-4 VaR-Bounded Positioning Contract

- PQTS shall compute per-strategy and portfolio VaR guardrails and bound position sizing/entry when projected VaR breaches budget.
- VaR methodology and confidence level shall be explicit, versioned, and visible in decision artifacts.

### GIPP-5 Real-Time Mispricing Scan Contract

- PQTS shall support continuous market scanning for pricing inefficiency candidates with bounded evaluation latency and stale-data protections.
- Candidate discovery events shall be traceable from market snapshot to final execution/risk decision.

### GIPP-6 Dynamic Risk Rebalance Contract

- During open positions, PQTS shall continuously recompute edge/EV/risk state and rebalance exposure (reduce/hold/exit) under policy controls.
- Rebalance actions shall emit reason codes tied to changed probabilities, volatility, liquidity, or risk budget state.

### GIPP-7 Public-Grade Transaction Provenance Contract

- PQTS shall export verifiable transaction ledgers for paper/live runs, including timestamp, market, side, size, rationale metrics, and realized outcome.
- Export format shall support human-readable public summaries and machine-readable audit bundles without exposing secrets.

### GIPP-8 Agent Skill Prompt Governance Contract

- If LLM-assisted strategy components are used, PQTS shall version and test skill/prompt artifacts as first-class configuration with reproducibility metadata.
- Any model-assisted recommendation that affects capital shall include policy-bound validation and fallback behavior on model unavailability.

## 67. X Post Assimilation Requirements (MarikWeb3, March 10, 2026)

These requirements are distilled from the referenced X post and linked wallet behavior, normalized into auditable system contracts.

Observed source links:
- `https://x.com/MarikWeb3/status/2031397014794060074?s=20`
- `https://polymarket.com/@distinct-baguette?via=Marik` (wallet link referenced in post)

### MARIK-1 Spread-Harvest Strategy Contract

- PQTS shall support explicit spread-harvest strategy mode where expected edge is sourced from bid/ask dislocations rather than directional outcome prediction.
- Strategy artifacts shall label this mode as market-making/spread-capture and separate its KPIs from directional alpha strategies.

### MARIK-2 Two-Sided Orderbook Participation Contract

- PQTS shall support synchronized two-sided participation logic (YES/NO or equivalent opposing market sides) with bounded exposure per market.
- Order lifecycle telemetry shall preserve per-side entry/exit and realized edge decomposition.

### MARIK-3 Inventory-Neutrality Guardrail Contract

- Spread-harvest strategies shall enforce inventory-neutrality constraints with configurable maximum net directional exposure and auto-rebalance/flatten actions.
- Breaches of neutrality bounds shall emit typed incident events and trigger policy-defined mitigation.

### MARIK-4 Hold-Time Bounded Capture Contract

- PQTS shall support bounded hold-time policies (for example short horizon minutes-scale exits) for spread-capture strategies.
- Policies shall include TTL exit, timeout cancellation, and emergency unwind behavior with auditable reason codes.

### MARIK-5 Panic-Flow Pattern Detector Contract

- PQTS shall provide orderbook microstructure detectors for panic/imbalance flow patterns that increase spread-capture opportunity.
- Detector outputs shall be versioned features with confidence scores and stale-data protections.

### MARIK-6 Per-Trade Edge Attribution Contract

- PQTS shall compute and persist realized PnL attribution per completed cycle as spread-capture components (for example `delta_bid_capture`, `delta_ask_capture`) plus costs.
- Aggregated attribution shall reconcile exactly to realized strategy PnL.

### MARIK-7 High-Turnover Safety Budget Contract

- For high-turnover spread strategies, PQTS shall enforce daily action budgets (order count, cancel/replace rate, fee budget, and slippage budget).
- Budget exhaustion shall degrade strategy state to reduce-only/hold according to policy.

### MARIK-8 Pattern-Watch Replication Harness Contract

- PQTS shall provide a replay/simulation harness that can evaluate identified wallet/orderbook behavioral motifs against historical market tapes.
- Harness outputs shall include reproducible motif detection precision, fill-rate, reject-rate, and realized net edge after costs.

## 68. X Post Assimilation Requirements (dunik_7, March 10, 2026)

These requirements are distilled from the referenced X post and linked wallet behavior, normalized into auditable system contracts.

Observed source links:
- `https://x.com/dunik_7/status/2031316903172489468?s=20`
- `https://polymarket.com/@BoneReader?via=999` (wallet link referenced in post)

### DUNIK-1 Multi-Signal Short-Horizon Feature Contract

- PQTS shall support short-horizon feature fusion using exchange orderbook state, on-chain context, funding signals, and near-term realized volatility windows.
- Feature windows and normalization rules shall be versioned and reproducible per strategy run.

### DUNIK-2 Bayesian Probability Engine Contract

- PQTS shall provide a Bayesian probability estimation module for event-outcome markets with explicit priors, likelihood updates, and posterior confidence outputs.
- Posterior probability and confidence artifacts shall be stored per candidate decision.

### DUNIK-3 Minimum Edge Threshold Gate Contract

- PQTS shall enforce configurable minimum edge thresholds (for example strategy default `edge_min = 4%`) before order submission.
- Threshold checks shall be cost-adjusted and include fees/slippage assumptions.

### DUNIK-4 High-Probability Entry Band Contract

- PQTS shall support parameterized high-probability entry bands (for example 90-95 cent price zones in binary outcome markets) for low-margin capture strategies.
- Entry band policies shall include spread/liquidity validation and adverse-selection safeguards.

### DUNIK-5 High-Frequency Throughput and Concurrency Contract

- PQTS shall support high-frequency, high-count trade loops with bounded per-market and portfolio-level concurrency limits.
- The runtime shall expose throughput, queue depth, and action budget telemetry to prevent overload-driven risk.

### DUNIK-6 Cross-Venue Confirmation Contract

- PQTS shall support cross-venue reference checks (for example centralized exchange momentum/price context) before opening event-market positions.
- Cross-venue dependencies shall include freshness checks and degrade-to-safe behavior on missing or stale feeds.

### DUNIK-7 Latency-Bounded Exit Contract

- PQTS shall support latency-bounded exit policies intended to close positions before expected market repricing windows.
- Exit latency targets, timeout paths, and fallback unwind behavior shall be configurable and auditable.

### DUNIK-8 Micro-Edge Attribution and Scale Accounting Contract

- PQTS shall attribute realized performance as micro-edge accumulation metrics (per-trade cents captured, turnover, and net after costs) with full reconciliation.
- Reporting shall separate directional alpha from microstructure capture to avoid metric contamination.

## 69. X Post Assimilation Requirements (zerqfer, March 10, 2026)

These requirements are distilled from the referenced X post and normalized into auditable system contracts.

Observed source links:
- `https://x.com/zerqfer/status/2031430737526747405?s=20`

### ZERQ-1 Pre-Trade Math Verification Gate Contract

- PQTS shall run pre-trade mathematical validation on each candidate order, including formula integrity checks for EV, volatility inputs, and sizing equations before routing.
- Trades failing math verification shall be blocked with explicit reason codes and persisted diagnostics.

### ZERQ-2 Multi-Agent Challenger Review Contract

- PQTS shall support a challenger review layer where independent analysis agents evaluate trade candidates from the primary strategy engine before execution.
- Challenger recommendations shall be policy-bound (`allow`, `warn`, `block`) with auditable vote rationale.

### ZERQ-3 Bug-Class Detection Rules Contract

- PQTS shall maintain a ruleset for edge-killing bug classes (for example decimal/scale errors, stale volatility windows, sign errors, malformed Kelly inputs) and test them on candidate trades.
- Rules shall be versioned and regression-tested against historical incident replays.

### ZERQ-4 Prevented-Trade Accountability Contract

- PQTS shall track and report prevented trades separately from executed trades, including prevented notional, prevented downside estimate, and counterfactual outcome where available.
- Daily reports shall include `executed_count`, `blocked_count`, and quality metrics for block decisions.

### ZERQ-5 Binary Fair-Value Model Registry Contract

- PQTS shall maintain an explicit registry of binary-outcome fair-value models (including Black-Scholes-derived adaptations where used), each with assumptions, calibration method, and validity bounds.
- Strategy configs shall reference registry IDs instead of ad-hoc inline model formulas.

### ZERQ-6 Short-Interval Imbalance Scanner Contract

- PQTS shall support short-interval orderbook imbalance scanning with configurable cadence (default target in the 10-30 second range), freshness checks, and backpressure handling.
- Scanner outputs shall include timestamped imbalance features consumable by execution/risk modules.

### ZERQ-7 Pluggable Context Engine Contract

- PQTS shall support pluggable context engines (for example wallet-flow trackers, venue context enrichers, news/state features) through typed interfaces and isolated failure behavior.
- Context-engine failures shall degrade safely and never bypass hard risk/kill-switch controls.

### ZERQ-8 Real-Time Review Latency Budget Contract

- Pre-trade review layers shall operate under explicit latency budgets with fail-closed or degrade-to-safe policy selection per strategy stage.
- Budget adherence and timeout outcomes shall be observable in execution telemetry and SLO reporting.

## 70. X Post Assimilation Requirements (antpalkin, March 10, 2026)

These requirements are distilled from the referenced X post and linked product context, normalized into auditable system contracts.

Observed source links:
- `https://x.com/antpalkin/status/2031430305660215464?s=20`
- `http://terminal.polysigma.io/` (terminal link referenced in quoted content)
- `https://polymarket.com/@LastKnight` (example account link referenced in quoted content)
- `http://polysigma.io` (product link referenced in quoted content)

### ANTP-1 Indicator-Rich Prediction Terminal Contract

- PQTS shall provide a prediction terminal view for short-horizon markets with configurable indicator panels, market context overlays, and execution readiness state.
- Indicator calculations and data sources shall be inspectable from the UI and exportable in run artifacts.

### ANTP-2 Structured Beginner-to-Operator Playbook Contract

- PQTS shall ship a structured learning/playbook path that maps onboarding steps to concrete outcomes (demo, backtest, paper campaign, review).
- Each step shall reference exact commands/UI actions, expected artifacts, and clear pass/fail completion criteria.

### ANTP-3 Module-Based Curriculum Artifact Contract

- PQTS docs shall maintain moduleized training content (topic units with prerequisites and checkpoints) aligned to actual product workflows.
- Curriculum modules shall version-lock to release tags and fail CI on broken command/path references.

### ANTP-4 Continuous Update Cadence Transparency Contract

- PQTS shall publish a machine-readable changelog and weekly release summary for strategy, execution, and UI changes affecting operator behavior.
- The terminal/help surfaces shall expose “what changed” notices linked to release evidence.

### ANTP-5 Claims-to-Evidence Marketing Guardrail Contract

- Any public performance or precision claim shown in docs/UI shall link to reproducible evidence bundles with run config, timeframe, costs, and trust label.
- Unsupported promotional claims shall be blocked by docs/release validation checks.

### ANTP-6 Example Account Replication Contract

- When external accounts/wallets are cited as exemplars, PQTS shall provide internal replication harnesses that test the claimed behavior under explicit assumptions.
- Replication reports shall publish what was reproducible, what was not, and key uncertainty drivers.

### ANTP-7 Multi-Locale Documentation Accessibility Contract

- PQTS shall support multilingual documentation artifacts for core onboarding and safety workflows, with synchronization checks against canonical English docs.
- Translation status and staleness shall be surfaced in docs metadata.

### ANTP-8 Terminal Data Freshness and Latency Disclosure Contract

- Prediction terminal pages shall display explicit data freshness, ingestion lag, and indicator recompute latency badges.
- If freshness or latency thresholds are breached, terminal recommendations shall degrade to warning/hold mode and log diagnostic events.

## 71. External Assimilation Requirements (Hedgeye "Master The Market", January 29, 2025)

These requirements are distilled from the referenced material and normalized into auditable system contracts.

Observed source links:
- `https://info.hedgeye.com/master-the-market`
- `https://storage.pardot.com/764243/1738158424MLZsUu3O/eBook_1.29.2025.pdf`
- Local user-provided copy: `/Users/jay/Document (Lcl)/master the market.pdf`

### MTM-1 Preserve-Protect-Compound Objective Contract

- PQTS shall enforce portfolio objectives in priority order: preserve capital, protect against large drawdowns, then compound returns.
- Strategy scorecards and promotion gates shall include objective compliance checks before considering return optimization.

### MTM-2 Drawdown Recovery Math Contract

- PQTS shall compute and display required recovery return after drawdowns and use that metric in risk budgeting and escalation policies.
- If projected recovery burden exceeds configured tolerances, the system shall tighten exposure and require explicit operator acknowledgment.

### MTM-3 Rate-of-Change Regime Engine Contract

- PQTS shall support a regime engine based on year-over-year rate-of-change inputs for growth and inflation, with explicit policy overlays.
- Regime transitions shall be backtestable and emitted as structured events consumable by allocation and execution modules.

### MTM-4 Four-Quadrant Regime Mapping Contract

- PQTS shall maintain a four-quadrant mapping of growth/inflation acceleration states with predefined risk postures and preferred/avoided asset exposures.
- Quadrant mappings shall be versioned, evidence-backed, and linked to realized outcome reports.

### MTM-5 Top-Down plus Bottom-Up Fusion Contract

- PQTS shall require that deployable strategy decisions can be decomposed into top-down macro context and bottom-up security/execution evidence.
- Conflict between macro and micro signals shall trigger policy-defined sizing reductions or hold decisions.

### MTM-6 Multi-Horizon Signal Stack Contract

- PQTS shall expose a standardized multi-horizon signal stack (short, intermediate, long) for every tradable instrument.
- Signal state transitions shall support breakout/breakdown detection and be auditable in decision traces.

### MTM-7 Price-Volume-Volatility Range Model Contract

- PQTS shall provide a quantitative probable-range model using price, volume, and volatility inputs to generate actionable buy/sell zones.
- Range model outputs shall include confidence and phase-transition flags with replay validation support.

### MTM-8 Position Sizing Ladder Contract

- PQTS shall enforce per-asset-class minimum/maximum position sizing bounds calibrated by realized/implied volatility class.
- Position adjustments shall be executed in configurable basis-point ladders with explicit anti-overconcentration checks.

### MTM-9 Buy-Dip and Exit Rules Contract

- PQTS shall implement rule-based dip-buy and exit logic tied to multi-horizon support/break conditions and range-structure signals.
- Exit hierarchy shall include reduce, minimum-position, and full-exit states with machine-verifiable trigger criteria.

### MTM-10 Stop-Loss and Process-Override Contract

- PQTS shall support hard stop-loss controls that become stricter as conviction transitions from thesis to risk containment mode.
- Manual override of stop or sizing rules shall require reason capture, approval policy checks, and post-mortem tagging.

### MTM-11 Systematic-Flow Pressure Monitor Contract

- PQTS shall monitor systematic flow proxies (for example volatility shocks, forced de-risking indicators, and liquidity stress) and translate them into risk posture adjustments.
- Flow-pressure alerts shall be linked to potential cascade buy/sell scenarios and recommended mitigation actions.

### MTM-12 Mistake Taxonomy and Learning Loop Contract

- PQTS shall maintain a mistake taxonomy (model error, data staleness, sizing breach, process violation, narrative bias, etc.) for every adverse event.
- Weekly process reviews shall aggregate taxonomy outcomes and automatically generate prioritized remediation tasks.

## 72. UI Legitimacy and Star-Magnet Surface Requirements (March 11, 2026)

These requirements enforce one coherent public UI surface with explicit trust/provenance and professional-grade operator workflows.

### UXL-1 Web-Primary Surface and Runtime Contract

- Next.js (`apps/web`) shall be the primary public UI surface for active release phases.
- Dash shall be explicitly labeled operator fallback and shall not be the default public launch path.
- Docker/README/quickstart flows shall default to web + API startup paths and place Dash behind an explicit operator profile.

### UXL-2 Canonical Backend Ownership for UI State

- Next.js route handlers for assistant and onboarding flows shall proxy canonical FastAPI endpoints and shall not keep authoritative in-memory domain state.
- Canonical backend endpoints shall expose onboarding run creation/status and assistant turn responses with correlation metadata.

### UXL-3 Global Trust Bar Completeness Contract

- Trust bar shall be visible on all dashboard pages and include workspace, environment, account, venue, data freshness, native-hotpath status, kill-switch status, and trace/run identifiers.
- Trust bar shall include live stream-health indicators for risk and execution channels.

### UXL-4 Provenance Drawer Standard

- Command center, benchmarks, execution, and order-truth pages shall expose one-click provenance drawers.
- Provenance drawers shall include trust label, generation timestamp, source artifact path, report path, and leaderboard path.

### UXL-5 Execution Explainability Grid Contract

- Execution surface shall include an explainability grid mapping order lifecycle stages: signal, risk gate, router/venue, and fill outcome.
- Each explainability row shall deep-link into per-order truth drilldown.

### UXL-6 Browser-First Onboarding Runtime Contract

- Onboarding wizard execution shall run against canonical backend run state with deterministic progress snapshots.
- UI shall support browser-first onboarding without requiring CLI for first meaningful result, while still exposing code-visible command equivalents.

### UXL-7 Studio Visual System Legitimacy Contract

- Web UI shall use a tokenized design system with explicit typography tokens, semantic status colors, spacing scale, and responsive behavior.
- Core tables/chips/cards shall render from shared style primitives to prevent ad hoc visual drift.

### UXL-8 Public README Trust-Surface Contract

- README shall present web-primary startup, trust/provenance surfaces, and benchmark evidence above the fold.
- Visual tour media references shall resolve correctly in repository contexts and regeneration workflow shall remain documented and runnable.

## 73. Additional Delta Requirements from External Post Chain (hanakoxbt OSINT stack, March 10, 2026)

These requirements capture net-new, applicable deltas from the referenced X post and its included links while preserving existing hard safety and provenance controls.

Observed source links:
- `https://x.com/hanakoxbt/status/2031439843440710064?s=20`
- `https://kreo.app/@1743116` (included short-link target referenced in post thread)

### HKO-1 Multi-Source Event-Intel Ingestion Contract

- PQTS shall support ingesting multiple public event-intel feeds (for example shipping, satellite-derived, news, or social signal streams) through typed adapters.
- Every feed adapter shall emit normalized event records with source, timestamp, confidence, and ingestion-lag fields.
- Missing/late feeds shall degrade strategy outputs to hold/reduce states under policy rather than silently proceeding.

### HKO-2 Geotemporal Entity-Linking Contract

- PQTS shall provide geotemporal linking that maps external event records to tradable market entities with explicit uncertainty scores.
- Link decisions shall store `event_id -> market_id` mappings, matching rationale, and expiry/refresh windows for replayability.
- Low-confidence links shall be blocked from live candidate generation until corroboration thresholds are met.

### HKO-3 Corroboration-First Trigger Gate Contract

- Lead-lag trade triggers sourced from external event-intel shall require minimum corroboration across independent sources before order submission.
- Corroboration policy shall be configurable by strategy stage (`paper`, `shadow`, `canary`, `live`) with stricter live thresholds.
- Trigger diagnostics shall include corroborating source IDs, timestamps, and time-skew checks.

### HKO-4 Event-to-Quote Causal Alignment Contract

- Candidate generation shall enforce causal ordering between event-intel timestamps and market quote snapshots, with anti-lookahead validation.
- If causal order cannot be proven (clock skew, stale quote, ambiguous event time), the candidate shall be blocked and logged.
- Replay mode shall reproduce causal alignment checks identically to live/paper paths.

### HKO-5 External Signal Provider Boundary Contract

- External signal providers referenced by linked pages (for example Kreo-linked channels) shall be integrated only through read-only, provenance-tagged ingestion interfaces.
- Provider-derived signals shall never bypass `RiskAwareRouter` or existing kill-switch/risk gates.
- Provider health, schema drift, and entitlement status shall be surfaced in trust/provenance telemetry.

### HKO-6 Pre-Trade Evidence Bundle Contract

- Every order candidate sourced from event-intel signals shall produce a compact pre-trade evidence bundle with:
  - matched event records,
  - corroboration summary,
  - causal alignment checks,
  - latency metrics,
  - net-EV/risk-gate decision.
- Evidence bundles shall be persisted with run/trace identifiers and be queryable from execution explainability views.

### HKO-7 Precision-Claim Governance Contract

- Public precision/ROI claims for event-intel strategies (for example high win-rate or precision percentages) shall be marked `unverified` unless backed by reproducible benchmark bundles.
- Any promoted claim shall link to timeframe, sample size, trust label, and trade-level accounting artifacts.

### HKO-8 Capacity and Decay Monitoring Contract

- PQTS shall track realized edge for event-intel strategies as function of signal latency bucket and concurrent trade load.
- If edge decays beyond configured thresholds under higher load, strategy size and concurrency limits shall auto-tighten.
- Decay breaches and mitigation actions shall be emitted as typed risk/incidence events.

## 74. Additional Delta Requirements from External Post Chain (Shelpid_WI3M multi-agent execution, March 10, 2026)

These requirements capture net-new, applicable workflow mechanics from the referenced X post and linked surfaces while excluding unverified promotional performance claims.

Observed source links:
- `https://x.com/Shelpid_WI3M/status/2031361973871374759?s=20`
- `https://x.com/claudeai/status/2031088171262554195`
- `https://polymarket.com/@vidarx?via=shelpid`
- `https://t.me/KreoPolyBot?start=ref-shelpid`

### SWI-1 Parallel Analyst/Verifier Agent Contract

- Signal generation from external narrative/event sources shall run through parallel specialist agents with explicit role labels (for example hypothesis, contradiction, and execution-feasibility).
- Candidate promotion to order intent shall require at least one independent verifier agent pass and an explicit disagreement score.
- Agent outputs shall include role-local evidence references and confidence values for replayability.

### SWI-2 High-Signal Decision Packet Contract

- Multi-agent analysis shall collapse to one deterministic decision packet per candidate (`allow`, `reduce`, `hold`, or `block`) instead of unranked free-form summaries.
- Decision packets shall include ranked blocker/warning findings with severity, reason codes, and traceable evidence pointers.
- If ranked findings conflict across agents beyond configured thresholds, default action shall be `hold` or `block`.

### SWI-3 Complexity-Scaled Analysis Budget Contract

- Analysis depth (model/tool passes, context size, latency budget) shall scale with candidate complexity and uncertainty class.
- Every cycle shall log token/cost/latency usage with per-candidate budget policy identifiers.
- Budget overruns or timeout breaches shall fail closed to `hold`/`reduce` under stage policy.

### SWI-4 Confidence-Calibrated Sizing Contract

- Position sizing for agent-derived candidates shall be confidence-calibrated and stage-bounded; fixed-size default sizing shall be disallowed outside explicit diagnostic mode.
- Confidence-to-size mapping shall be versioned and revalidated when model/prompt/workflow versions change.
- Calibration drift beyond policy thresholds shall auto-tighten sizing and raise a typed risk event.

### SWI-5 Workflow Determinism and Prompt-Drift Guard Contract

- Agent workflow templates, routing logic, and prompt bundles shall be versioned and hash-pinned per run.
- Live/canary execution shall reject ad-hoc prompt mutations unless explicitly approved and audit-logged.
- Promotion gates shall require parity checks proving paper/shadow/live use the same versioned workflow bundle.

### SWI-6 Copytrade/Wallet Signal Boundary Contract

- External copytrade or public-wallet-derived signals shall enter PQTS only through read-only adapters with provenance, freshness, and trust labels.
- Mirroring behavior shall be treated as a strategy hypothesis requiring replay/paper validation before canary/live eligibility.
- External signal paths shall never bypass `RiskAwareRouter`, kill-switches, or stage-gate controls.

### SWI-7 Source Reliability and Claim Handling

- Public claims from this source chain about overnight profit, win rate, or rapid bot build-out shall be marked `unverified` unless backed by reproducible trade-level artifacts.
- Requirements adopted from this source chain shall remain limited to observable system mechanics and validated control patterns.

## 75. Additional Delta Requirements from External Post Chain (AleiahLock copytrade follow-up, March 10, 2026)

These requirements capture net-new, applicable deltas from the referenced post and linked surfaces, focused on statistical claim hygiene and referral-aware copytrade safety.

Observed source links:
- `https://x.com/AleiahLock/status/2031374104163414452?s=20`
- `https://polymarket.com/profile/0x84571f1bf97a5c710cbe51daff2dd4556cc887fd?tab=positions?via=aleiah`
- `http://ratio.you/r/BP9FKCC4`

### AL-11 Public-Profile Metric Reconciliation Contract

- Any externally cited wallet/profile performance metrics (for example win rate, prediction count, or total PnL) shall be reconciled into a normalized schema that separates:
  - realized closed PnL,
  - unrealized mark-to-market PnL,
  - fees/slippage-adjusted net PnL,
  - evaluation window.
- PQTS shall reject promotional metric ingestion when required decomposition fields are missing.
- Reconciled profile metrics shall include source timestamp and profile snapshot hash for replayability.

### AL-12 Win-Rate Statistical Confidence Contract

- Headline win-rate claims sourced from public profiles shall include minimum sample-size and confidence-interval calculations before eligibility in strategy evaluation.
- Win-rate claims without explicit window boundaries or with unstable confidence bands shall be downgraded to `diagnostic_only` or `unverified`.
- Strategy promotion logic shall not use win-rate claims alone without paired expectancy/PnL-quality evidence.

### AL-13 Sponsored/Referral Influence Disclosure Contract

- External posts containing referral or promotional links (for example `?via=` or referral codes) shall be flagged with sponsorship/incentive-risk metadata.
- Sponsored/incentive-flagged sources shall be down-weighted by default in signal trust scoring and blocked from direct auto-promotion pathways.
- Decision artifacts shall persist disclosure flags and weighting effects for audit.

### AL-14 Copytrade Safe-Onboarding and Claim-Boundary Contract

- Copytrade pathways sourced from third-party promotional apps shall enforce explicit safe-onboarding gates (paper-first, per-leader caps, max daily loss, market allowlist).
- UI/docs flows shall block “follow in 1 minute” style live-capital shortcuts unless safety gates are completed and acknowledged.
- Public claims from this source chain about near-perfect win rates or large PnL totals shall remain `unverified` unless reproducible trade-level evidence with bounded timeframe is available.

## 76. Additional Delta Requirements from External Post Chain (LCSeekers LMSR claim follow-up, March 11, 2026)

These requirements capture net-new, applicable deltas from the referenced post while resolving mechanism claims against primary venue documentation.

Observed source links:
- `https://x.com/LCSeekers/status/2031417265921446236?s=20`
- `https://docs.polymarket.com/developers/CLOB/introduction`
- `https://docs.polymarket.com/trading/overview`

### LCS-1 Venue Mechanism Ground-Truth Registry Contract

- PQTS shall maintain a machine-readable venue/market mechanism registry (`clob`, `amm`, `lmsr`, or `hybrid`) with source URL, verification timestamp, and owner.
- Strategy execution shall be blocked when the target venue has no verified mechanism profile.
- Mechanism registry updates shall be audit-logged and replay-addressable.

### LCS-2 Assumption-Bound Model Routing Contract

- Every strategy and fill model shall declare required mechanism assumptions (for example `requires: clob` or `requires: lmsr`).
- Runtime shall route to mechanism-compatible pricing/fill logic only; incompatible paths shall fail closed with structured reason codes.
- Promotion artifacts shall include proof that paper/canary/live all used mechanism-compatible routing.

### LCS-3 External Claim Contradiction Governance Contract

- If external educational/promotional claims conflict with primary venue docs (for example LMSR vs CLOB), PQTS shall persist a contradiction record and downgrade claim trust to `unverified`.
- Contradictory claims shall not be used as execution assumptions unless primary-source evidence is attached.
- Contradiction records shall be visible in provenance/explainability views.

### LCS-4 Self-Impact-Adjusted Edge Contract

- Edge estimation shall include self-impact-adjusted expected value, not only point-in-time market mispricing (`p_true - p_market`).
- Candidate sizing shall use impact-aware EV curves; strategies with non-positive impact-adjusted EV at target size shall auto-reduce or block.
- Diagnostics shall expose raw EV vs impact-adjusted EV deltas per candidate.

### LCS-5 Capacity and Crowding Stress Contract

- PQTS shall run periodic capacity stress tests that sweep order size and concurrent load to estimate edge decay and break-even size.
- Promotion to canary/live shall require passing configured edge-decay thresholds at intended capital bands.
- Breaches in live/canary shall trigger automatic size/concurrency tightening and incident emission.

### LCS-6 Liquidity Realism Contract

- CLOB venues shall never be treated as infinite-liquidity sinks; execution planning must use observed depth, spread, and partial-fill likelihood.
- Fill simulations and live diagnostics shall report depth-consumption and partial-fill metrics for each submitted order batch.
- Any fallback assumption that implies guaranteed fills shall be restricted to labeled diagnostic mode only.

## 77. Additional Delta Requirements from External Review Feedback (ChatGPT assessment, March 11, 2026)

These requirements capture net-new closure criteria from the referenced platform assessment, focused on eliminating remaining architecture/trust inconsistencies.

Observed source links:
- `https://github.com/jakerslam/pqts`
- `https://github.com/jakerslam/pqts/blob/main/docs/HUMAN_DECISIONS_LOG.md`
- `https://github.com/jakerslam/pqts/blob/main/docs/BENCHMARKS.md`
- `https://github.com/jakerslam/pqts/tree/main/apps/web`
- `https://raw.githubusercontent.com/jakerslam/pqts/refs/heads/main/config/integrations/official_integrations.json`
- `https://github.com/jakerslam/pqts/blob/main/docs/USER_RESEARCH_2026_03.md`

### CGPT-1 Canonical Web/API Contract Closure

- The Next.js frontend shall consume one canonical typed API contract generated from FastAPI OpenAPI definitions.
- Client paths that do not map to canonical backend endpoints (for example orphan `/api/v1/*` aliases) shall fail CI contract checks.
- Contract drift (removed/renamed backend fields or routes) shall block release promotion until web/API parity tests pass.

### CGPT-2 Thin-Client Runtime Integrity

- Production web runtime shall not read repository files directly for portfolio, benchmark, replay, or execution-truth data.
- Production web runtime shall not execute local subprocess jobs (for example `python3 ...`) for user-facing API actions.
- Any local-file/local-process development shortcuts must be explicitly dev-scoped, feature-flagged, and visibly labeled in UI diagnostics.

### CGPT-3 Onboarding Single-Truth Contract

- PQTS shall expose one canonical beginner onboarding path (package-first) and one explicitly labeled advanced source/developer path.
- README, quickstart docs, CLI help, and PyPI metadata shall present identical canonical first-success commands and safety defaults.
- If onboarding content diverges across these surfaces, governance checks shall fail and block release.

### CGPT-4 Documentation Product Surface Reliability

- Public documentation links in README, package metadata, and release notes shall resolve to a live canonical docs surface.
- Docs link availability and key page integrity checks shall run in CI/release gates.
- Broken docs links or mismatched canonical docs targets shall block release publication.

### CGPT-5 Integration Maturity Claim Parity

- Public multi-market positioning shall be constrained by the canonical integration index and maturity states (`active`, `experimental`, `certified`).
- Marketing/README claims shall not present `experimental` adapters as certified live-ready integrations.
- Integration maturity transitions shall require evidence artifacts and explicit state changes in the canonical registry.

### CGPT-6 External Validation Readiness Contract

- “Noob-friendly” and “pro-ready” release claims shall require external cohort evidence, not internal-proxy-only runs.
- Cohort artifacts shall include participant mix, task completion, time-to-first-success, and top friction findings.
- Release readiness gates shall downgrade maturity claims when external cohort thresholds are unmet.

### CGPT-7 Benchmark Continuity and Progress Integrity

- Benchmark program outputs shall preserve both historical weak baselines and current reference bundles to prove directional progress honestly.
- Reference summaries shall exclude `diagnostic_only` and `unverified` runs by policy and verify this exclusion in CI.
- Benchmark publication shall require trust-label/provenance fields and machine-readable run lineage.

### CGPT-8 Distribution Truth and Version Cohesion Contract

- Version, release, package, and API runtime identifiers shall remain synchronized across `pyproject`, tags/releases, package index, and API service metadata.
- Release gates shall validate distribution truth consistency before publish steps execute.
- Any truth-layer contradiction (version mismatch, stale release pointers, invalid install/doc claims) shall block promotion until resolved.

## 78. Additional Delta Requirements from External Post Chain (AlterEgo weather-bot v2, March 11, 2026)

These requirements capture net-new, applicable deltas from the referenced post chain without duplicating existing weather/EV/Kelly baseline contracts already present in AX/PL/QF families.

Observed source links:
- `https://x.com/AlterEgo_eth/status/2031719370431615010?s=20`
- `https://x.com/i/article/2030169969804333057` (quoted-link target, login-gated)

### AEG-1 In-Position Forecast Drift Exit Contract

- Weather-market strategies shall continuously monitor forecast updates for open positions and compute post-entry forecast drift against the entry snapshot.
- Material adverse drift beyond configured thresholds shall trigger deterministic protective actions (`reduce`, `close`, or `halt`) with explicit reason codes.
- Drift-triggered exits shall be replayable with archived entry forecast, updated forecast, and computed drift metrics.

### AEG-2 Minute-Cadence Monitoring Contract

- Weather strategy runtime shall support a configurable high-frequency monitoring cadence (default 60 seconds) while positions are open.
- Missed monitor cycles, stale forecast payloads, or update-fetch failures shall fail closed to safe-position actions and incident logging.
- Monitoring cadence, skipped cycles, and stale-duration metrics shall be exposed in execution/risk telemetry.

### AEG-3 City-Month-Bucket Self-Calibration Contract

- Calibration subsystem shall maintain residual/error surfaces keyed by at least city, calendar month, and market bucket.
- Strategy probability outputs shall apply these residual adjustments when sufficient local sample support exists and confidence criteria are met.
- Calibration adjustments shall be versioned and rollback-capable; low-sample segments shall fall back to global calibration policies.

### AEG-4 Trade-Outcome Feedback Dataset Contract

- For each weather trade, system shall persist calibration feedback fields including:
  - city/market location key,
  - month/season key,
  - bucket/contract key,
  - forecast probability at entry,
  - realized outcome.
- Feedback records shall be appended in an immutable, provenance-tagged dataset suitable for deterministic recalibration replay.
- Missing feedback fields shall block inclusion of that trade in calibration update passes.

### AEG-5 Calibrated-Probability EV Gate Contract

- EV-gate decisions shall require calibrated probability inputs with explicit provenance (source(s), calibration version, timestamp).
- If calibrated probability provenance is missing or stale, order candidates shall be blocked rather than evaluated on uncalibrated estimates.
- Decision artifacts shall include both raw and calibrated probability values used by EV/Kelly stages.

### AEG-6 Source Reliability and Claim Handling

- Public claims about rapid intraday bankroll growth from weather bots shall be marked `unverified` unless backed by reproducible, trade-level artifacts with bounded evaluation windows.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated inferred controls.

## 79. Additional Delta Requirements from External Post Chain (0xPhilanthrop follow-up, March 11, 2026)

These requirements capture net-new, applicable deltas from the referenced post while avoiding duplication of existing two-sided, hedge, and copytrade safety contracts.

Observed source links:
- `https://x.com/0xPhilanthrop/status/2031459815818424804?s=20`
- `https://t.me/KreoPolyBot?start=ref-53blg718p7` (post body link)
- `https://polymarket.com` (post body link)

### PHL-1 Short-Cadence Spread Scanner Contract

- Short-horizon spread-loop strategies shall support configurable scanner cadence with default `5s` cycle interval.
- Each scan cycle shall persist candidate snapshot metadata including timestamp, per-leg executable quotes, and depth context.
- Missed-cycle and stale-snapshot conditions shall emit typed incidents and fail closed to `hold` until scanner health recovers.

### PHL-2 Overround-Capped Two-Sided Loop Gate Contract

- System shall support a two-sided spread-loop gate using a configurable combined-quote cap (default source profile: `YES + NO <= 1.02`).
- Candidate acceptance shall require fee/slippage-adjusted non-negative expectancy and explicit hedge-feasibility checks.
- Cycles with combined quote above cap or negative post-cost expectancy shall be blocked with structured reason codes.

### PHL-3 Rapid Fill-State Loop Transition Contract

- If one leg fills first, runtime shall invoke immediate hedge workflow under configured max-latency and max-slippage budgets.
- If both legs fill in loop mode, runtime shall execute deterministic neutral-exit/position-close transition logic.
- Fill-state transitions (`none`, `one_leg`, `both_legs`, `hedged`, `closed`) shall be replayable with per-transition timing diagnostics.

### PHL-4 Source Reliability and Claim Handling

- Public claims from this source chain about overnight profit or simplicity-to-profit outcomes shall be marked `unverified` unless supported by reproducible trade-level artifacts.
- Requirements adopted from this source shall remain limited to observable mechanics and validated controls rather than promotional profitability claims.

## 80. Additional Delta Requirements from External Post Chain (morpphhhaw, March 11, 2026)

These requirements capture net-new, applicable deltas from the referenced weather-market post while avoiding duplication of existing weather-consensus and two-sided-loop controls.

Observed source links:
- `https://x.com/morpphhhaw/status/2031662402392011174?s=20`
- `https://ratio.you/r/8ASJG6JJ` (post body link)
- `https://polymarket.com/@ColdMath?via=morph` (post body link)

### MORP-1 Daily Tight-Range Weather Candidate Scoring Contract

- Weather strategy shall support ranking daily city-range markets by forecast-band tightness and implied-odds dislocation.
- Candidate scoring shall include market-specific range-width context and required edge buffer after cost assumptions.
- Markets failing minimum dislocation score thresholds shall be excluded before order placement.

### MORP-2 Ultra-Low Entry Band and Quote-Precision Contract

- Strategy shall support configurable ultra-low entry bands for weather outcomes (source-profile defaults include sub-cent levels such as `0.1-0.2` cents where venue precision permits).
- Order-construction logic shall enforce venue-precision-safe rounding and reject entries that lose asymmetry after rounding/fees.
- Entry-band overrides shall be versioned and validated via replay before promotion to canary/live.

### MORP-3 Passive Lowball Queueing and Fill-Quality Contract

- Strategy shall support passive lowball limit-order queueing mode with explicit queue-age and cancel/replace limits.
- Fill-quality telemetry shall distinguish passive-taken fills from aggressive execution paths and track adverse-selection outcomes.
- Stale-queue or deteriorating-fill-quality conditions shall auto-tighten order placement or pause the mode.

### MORP-4 Source Reliability and Claim Handling

- Public claims from this source chain about extreme single-market ROI or repeatability of near-zero-entry outcomes shall be marked `unverified` unless backed by reproducible trade-level evidence.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated controls rather than promotional profitability claims.

## 81. Additional Delta Requirements from External Post Chain (MisterNoComents, March 11, 2026)

These requirements capture net-new, applicable deltas from the referenced post focused on count-based event markets and range-strip arbitrage mechanics.

Observed source links:
- `https://x.com/MisterNoComents/status/2031556318276854171?s=20`
- `https://polymarket.com` (post body link)

### MNC-1 Count-Market Event Ingestion Contract

- PQTS shall support event-count market strategies that ingest live activity counters from external platforms (for example posts/replies/quotes) via versioned adapters.
- Counter ingestion shall persist source timestamp, event subtype breakdown, and integrity flags (missing window, API lag, schema drift).
- Strategies shall fail closed when count-source freshness or integrity falls below configured thresholds.

### MNC-2 Velocity Nowcast and Projection Contract

- For count-based markets, PQTS shall compute rolling event-velocity projections with uncertainty bands and explicit horizon target (for example end-of-week count).
- Projection artifacts shall include latest observed count, velocity estimate, uncertainty interval, and model version.
- Trade eligibility shall require projection confidence above stage-configured thresholds.

### MNC-3 Contiguous Range-Strip Arbitrage Contract

- PQTS shall support contiguous-range strip construction across mutually exclusive count buckets and compute total strip cost after fees/slippage.
- Strip execution shall be allowed only when post-cost strip cost is below configured payout floor and within selected target-window confidence.
- Range-strip decisions shall store covered bucket set, total cost, guaranteed-payout envelope, and residual out-of-window risk.

### MNC-4 Uncertainty-Collapse Exit Timing Contract

- Count-market strategies shall support early exit policies that monetize uncertainty collapse before final resolution when priced edge converges.
- Exit policies shall define minimum realized edge, liquidity/depth checks, and latest permissible hold horizon.
- Time-to-resolution edge decay and realized exit attribution shall be logged for replay and policy tuning.

### MNC-5 Source Reliability and Claim Handling

- Public claims from this source chain about guaranteed returns, extreme compounding, or deterministic overnight gains shall be marked `unverified` unless backed by reproducible trade-level evidence.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated controls rather than promotional profitability claims.

## 82. Additional Delta Requirements from External Post Chain (de1lymoon, March 11, 2026)

These requirements capture net-new, applicable deltas from the referenced post focused on indicator-rich directional classification and uncertainty-aware model gating.

Observed source links:
- `https://x.com/de1lymoon/status/2031750472395047364?s=20`
- Quoted context reference in post body: `Noisy (@noisyb0y1)` (thread mention)

### DLM-1 Next-Step Directional Target Contract

- Prediction-market directional models shall support explicit next-step classification targets (for example `target = 1` when next close/probability exceeds current, else `0`).
- Training/inference artifacts shall persist target-construction rules, horizon definition, and label version metadata.
- Strategy decisions shall clearly distinguish directional classification outputs from price-level forecasting outputs.

### DLM-2 Indicator-Fabric Governance Contract

- Indicator-rich models shall support versioned feature manifests that include indicator definitions, lookback windows, and compute dependencies.
- Feature pipelines shall validate freshness, null-rate bounds, and schema compatibility before inference.
- Feature-set changes shall require reproducible backtest/replay evidence before promotion.

### DLM-3 Monte-Carlo Dropout Uncertainty Contract

- Model runtime shall support Monte Carlo Dropout (or equivalent stochastic forward-pass uncertainty estimation) for directional classifiers.
- Inference artifacts shall persist predictive mean, uncertainty dispersion metrics, and sample-count configuration.
- Trade admission and sizing shall fail closed or downscale when uncertainty exceeds stage-policy limits.

### DLM-4 Throughput-Aware Multi-Market Classifier Operations

- Classifier pipelines operating across many markets shall enforce bounded inference latency budgets and per-cycle throughput caps.
- Runtime shall log market-count processed, inference latency distribution, and dropped/skipped candidates due to budget constraints.
- Capacity breaches shall degrade safely (`hold`/`reduce`) rather than silently executing with stale predictions.

### DLM-5 Source Reliability and Claim Handling

- Public claims from this source chain about win-rate, PnL, or guaranteed profitability shall be marked `unverified` unless backed by reproducible trade-level evidence.
- Requirements adopted from this source chain shall remain limited to observable mechanics and validated controls rather than promotional profitability claims.

## 87. Additional Delta Requirements from External Review Feedback (ChatGPT reassessment, March 12, 2026)

These requirements capture net-new, applicable deltas from the latest reassessment that were not yet explicit in prior CGPT closure requirements.

Observed source links:
- `https://github.com/jakerslam/pqts`
- `https://raw.githubusercontent.com/jakerslam/pqts/main/docs/BENCHMARKS.md`
- `https://raw.githubusercontent.com/jakerslam/pqts/main/results/reference_performance_latest.json`
- `https://raw.githubusercontent.com/jakerslam/pqts/main/docs/QUICKSTART_5_MIN.md`
- `https://raw.githubusercontent.com/jakerslam/pqts/main/docs/ISSUE_BACKLOG.md`

### CGPTR-1 Embedded Reference Artifact Trust/Provenance Contract

- `results/reference_performance_latest.json` shall carry explicit top-level `trust_label` and `provenance` fields as part of the canonical artifact contract.
- Each bundle entry in `reference_performance_latest.json` shall carry explicit `trust_label` and per-bundle `provenance` metadata fields.
- Governance/trust-surface checks shall fail when these fields are missing or invalid.

### CGPTR-2 Package-First Quickstart Contract Enforcement

- When `pypi.available=true`, `docs/QUICKSTART_5_MIN.md` shall include package-first commands (`pip install -U pqts`, `pqts quickstart --execute`) as the canonical beginner path.
- Source/developer setup shall remain available only as clearly-labeled advanced fallback.
- Truth-surface checks shall fail if package-first markers are missing while package distribution is declared available.

### CGPTR-3 Backlog Truth Partition Contract

- `docs/ISSUE_BACKLOG.md` shall remain explicitly labeled as historical issue templates when canonical active execution is tracked elsewhere.
- The canonical active execution order shall be documented in exactly one source (`docs/TODO.md`) and referenced from `docs/ISSUE_BACKLOG.md`.
- Any stale “future scaffold” references in backlog templates shall include status guidance preventing contradiction with implemented code paths.

## 88. Additional Delta Requirements from External Post Chain (Jeff Grimes portfolio-computer post, March 11, 2026)

These requirements capture applicable, testable deltas from the referenced post while preserving paper-first and hard safety controls.

Observed source links:
- `https://x.com/jeffgrimes9/status/2031839260069019894?s=20`
- `https://twitter.com/jeffgrimes9/status/2031839260069019894/video/1`
- Mentioned integration in post body: `@Plaid`

### JG-1 Plaid Brokerage Link Contract

- Runtime shall support a secure Plaid brokerage-link workflow exposed through canonical API endpoints.
- Link initiation shall issue bounded link-session tokens and persist link metadata without storing raw credentials.
- Link completion shall persist token fingerprints and connection metadata with explicit provider identity.

### JG-2 Multi-Account Portfolio Aggregation Contract

- Runtime shall aggregate balances across all linked brokerage accounts into one canonical portfolio totals payload.
- Aggregation output shall expose per-account and portfolio-level balances with timestamps.
- Aggregation responses shall remain available in read-only mode without requiring trading permissions.

### JG-3 Personal Always-On Terminal Contract

- Runtime shall expose a personalized terminal payload keyed by authenticated subject with persisted profile preferences.
- Terminal payload shall include account totals, sync health summary, and actionable next steps.
- Terminal surface shall advertise `always_on=true` semantics and deterministic refresh fields.

### JG-4 Read-Only-First Permission Contract

- Brokerage-link flows shall default to read-only permissions.
- Requests for trade-enabled permissions shall require explicit acknowledgement flags and remain blocked otherwise.
- Assistant responses shall remain analysis-only by default and never execute capital-affecting actions implicitly.

### JG-5 Sync Health and Fail-Closed Contract

- Linked brokerage connections shall expose sync-health status (`ok`, `stale`, `down`) with stale thresholds.
- Stale/down sync state shall set explicit fail-closed trade-block indicators.
- Manual sync actions shall emit deterministic receipts including synced IDs and timestamps.

### JG-6 Assistant Action Audit Contract

- Assistant turns shall write immutable audit rows with subject, requested action, capital-affecting flag, and timestamp.
- Capital-affecting intents shall be marked `requires_confirmation` and `executed=false` by default.
- Audit rows shall be queryable via a dedicated API surface for operator/compliance review.

### JG-7 Onboarding Sequence for Linked Portfolio Terminal

- Onboarding progression shall support: `connect brokerage` -> `aggregate accounts` -> `open personal terminal`.
- Each step shall emit machine-readable receipts suitable for regression tests.
- Missing connection prerequisites shall fail closed with explicit next-action guidance.

## 89. Additional Delta Requirements from Agent Pilotability Expansion (March 11, 2026)

These requirements capture the requested agent-pilotability expansion: stronger API control surface, self-service notification hooks, and a first-party Python agent library.

Observed source references:
- User directive (March 11, 2026): “super pilotable by an agent”
- Requested vectors: notification hooks, agent library, expanded API surface
- Operating constraints: `AGENTS.md`

### AGP-1 Canonical Agent Context Contract

- Runtime shall expose a canonical agent context endpoint (`/v1/agent/context`) that returns `system_facts`, `current_state`, and effective agent policy.
- `system_facts` shall include hard safety rules and allowed pilot action set.
- `current_state` shall include risk, promotion-stage summaries, and sync-health degradation summary required for pilot gating.

### AGP-2 Agent Capability and Budget Policy Contract

- Runtime shall support per-agent policy documents with explicit capabilities (`read`, `propose`, `simulate`, `execute`, `hooks_manage`).
- Policies shall include bounded pending-intent quotas and risk-budget fields.
- Policy updates shall be operator-gated and fail closed on invalid action/market policy payloads.

### AGP-3 Structured Pilot Intent Contract

- Runtime shall expose a canonical intent proposal endpoint (`/v1/agent/intents`) with required fields:
  `action`, `strategy_id`, `rationale`, `supporting_card_ids`, `current_metrics`, `gate_checks`, `risk_impact`.
- Unsupported actions or missing required fields shall be rejected with structured validation errors.
- Proposed intents shall be persisted with deterministic IDs and timestamps.

### AGP-4 Simulate-Before-Execute Gate Contract

- Runtime shall require successful simulation before any agent intent can execute.
- Simulation shall evaluate stage transition validity plus hard safety checks (kill-switch and sync-health fail-closed state).
- Failed simulation or failed gate checks shall block execution with explicit reasons.

### AGP-5 Operator-Controlled Execute Contract

- Intent execution shall require both:
  1) operator/admin identity and
  2) agent policy `execute=true`.
- Execute paths shall remain stage-constrained (`backtest -> paper -> shadow -> canary -> live`) and never skip hard gates.
- Execution shall update canonical promotion history with actor, action, and intent linkage.

### AGP-6 Immutable Agent Receipt Contract

- Propose, simulate, and execute operations shall emit immutable receipts with deterministic `receipt_id`, `intent_id`, `agent_id`, timestamp, and payload.
- Receipts shall be queryable via a dedicated endpoint (`/v1/agent/receipts/{receipt_id}`).
- Receipt artifacts shall support audit/replay of pilot decisions.

### AGP-7 Agent Notification Hook Governance Contract

- Runtime shall expose agent hook CRUD endpoints with explicit event typing (`intent_status`, `promotion_update`, `risk_incident`, `sync_health`).
- Hook registration shall enforce host allowlists, bounded quotas, retry/backoff bounds, and secret fingerprinting (no raw secret storage).
- Hook deletion shall be soft-delete with timestamped audit fields.

### AGP-8 First-Party Python Agent SDK Contract

- Runtime shall ship a first-party Python SDK wrapper for agent pilot endpoints (context, policy, intents, simulation, execution, receipts, hooks).
- SDK shall inject bearer auth deterministically and expose stable method names aligned to API resources.
- SDK behavior shall be covered by contract tests against FastAPI test surfaces.

### AGP-9 Fail-Closed Agent Safety Defaults Contract

- Default agent policy shall deny execution (`execute=false`) until explicitly enabled by operator policy update.
- Runtime shall deny execute requests for default policies even when caller has operator identity.
- Invalid hook/event/action payloads shall fail closed rather than silently degrade.
