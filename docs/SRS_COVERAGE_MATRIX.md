# SRS Coverage Matrix

This matrix is auto-generated from `docs/SRS.md`, `docs/TODO.md`, and repository evidence scans.

## Summary

- Total requirements: **445**
- implemented: **44**
- partial: **5**
- planned: **4**
- traced: **2**
- unmapped: **390**

## Prefix Summary

| Prefix | Implemented | Partial | Planned | Traced | Unmapped | Total |
|---|---:|---:|---:|---:|---:|---:|
| AC | 0 | 0 | 0 | 0 | 3 | 3 |
| AHF | 0 | 0 | 0 | 0 | 12 | 12 |
| AL | 0 | 0 | 0 | 0 | 10 | 10 |
| AR | 0 | 0 | 0 | 0 | 8 | 8 |
| AX | 0 | 0 | 0 | 0 | 10 | 10 |
| BF | 0 | 0 | 0 | 0 | 6 | 6 |
| COMP | 9 | 0 | 4 | 1 | 0 | 14 |
| CT | 0 | 0 | 0 | 0 | 8 | 8 |
| DK | 0 | 0 | 0 | 0 | 4 | 4 |
| DN | 0 | 0 | 0 | 0 | 5 | 5 |
| DV | 0 | 0 | 0 | 0 | 7 | 7 |
| DXR | 0 | 0 | 0 | 0 | 8 | 8 |
| FAUI | 0 | 0 | 0 | 0 | 12 | 12 |
| FDATA | 0 | 0 | 0 | 0 | 12 | 12 |
| FINGEN | 0 | 0 | 0 | 0 | 12 | 12 |
| FINQA | 0 | 0 | 0 | 0 | 10 | 10 |
| FR | 0 | 0 | 0 | 1 | 7 | 8 |
| GK | 0 | 0 | 0 | 0 | 9 | 9 |
| HD | 0 | 0 | 0 | 0 | 10 | 10 |
| HK | 0 | 0 | 0 | 0 | 10 | 10 |
| HL | 0 | 0 | 0 | 0 | 7 | 7 |
| HM | 0 | 0 | 0 | 0 | 7 | 7 |
| KL | 0 | 0 | 0 | 0 | 7 | 7 |
| LANG | 8 | 2 | 0 | 0 | 2 | 12 |
| LLE | 0 | 0 | 0 | 0 | 11 | 11 |
| MOAT | 13 | 3 | 0 | 0 | 0 | 16 |
| NFR | 0 | 0 | 0 | 0 | 3 | 3 |
| NS | 0 | 0 | 0 | 0 | 6 | 6 |
| OBBFD | 0 | 0 | 0 | 0 | 9 | 9 |
| PG | 0 | 0 | 0 | 0 | 7 | 7 |
| PH | 0 | 0 | 0 | 0 | 10 | 10 |
| PL | 0 | 0 | 0 | 0 | 7 | 7 |
| PMDESK | 0 | 0 | 0 | 0 | 12 | 12 |
| PMKT | 14 | 0 | 0 | 0 | 1 | 15 |
| PS | 0 | 0 | 0 | 0 | 7 | 7 |
| QF | 0 | 0 | 0 | 0 | 9 | 9 |
| RBI | 0 | 0 | 0 | 0 | 8 | 8 |
| RK | 0 | 0 | 0 | 0 | 9 | 9 |
| RP | 0 | 0 | 0 | 0 | 9 | 9 |
| RV | 0 | 0 | 0 | 0 | 4 | 4 |
| SECAPI | 0 | 0 | 0 | 0 | 10 | 10 |
| SH | 0 | 0 | 0 | 0 | 5 | 5 |
| TD | 0 | 0 | 0 | 0 | 6 | 6 |
| TVSRC | 0 | 0 | 0 | 0 | 9 | 9 |
| VR | 0 | 0 | 0 | 0 | 7 | 7 |
| WA | 0 | 0 | 0 | 0 | 9 | 9 |
| WCR | 0 | 0 | 0 | 0 | 8 | 8 |
| WF | 0 | 0 | 0 | 0 | 7 | 7 |
| WK | 0 | 0 | 0 | 0 | 10 | 10 |
| WR | 0 | 0 | 0 | 0 | 6 | 6 |
| XR | 0 | 0 | 0 | 0 | 7 | 7 |
| ZQ | 0 | 0 | 0 | 0 | 8 | 8 |

## Requirement Matrix

| ID | Title | Status | TODO | Evidence |
|---|---|---|---|---|
| FR-1 | Market Probability Normalization | traced | none | tests/test_generate_srs_gap_backlog_tool.py |
| FR-2 | Fair Probability Estimation | unmapped | none | - |
| FR-3 | Underdog Mispricing Signal | unmapped | none | - |
| FR-4 | Profitability Gate Integration | unmapped | none | - |
| FR-5 | Position Sizing | unmapped | none | - |
| FR-6 | Portfolio Constraints | unmapped | none | - |
| FR-7 | Exit and Lifecycle Rules | unmapped | none | - |
| FR-8 | Telemetry and Attribution | unmapped | none | - |
| NFR-1 | Latency | unmapped | none | - |
| NFR-2 | Reliability | unmapped | none | - |
| NFR-3 | Determinism | unmapped | none | - |
| AC-1 | Backtest Readiness | unmapped | none | - |
| AC-2 | Paper-Trade Readiness | unmapped | none | - |
| AC-3 | Promotion Gate | unmapped | none | - |
| BF-1 | Runtime Configuration and Boot Controls | unmapped | none | - |
| BF-2 | Market/Strategy Control Plane | unmapped | none | - |
| BF-3 | Mandatory Order and Risk Pipeline | unmapped | none | - |
| BF-4 | Market Data and Reliability Controls | unmapped | none | - |
| BF-5 | Research, Simulation, and Ops Automation | unmapped | none | - |
| BF-6 | Security, Compliance, and Data Governance | unmapped | none | - |
| RV-1 | Core Control Plane | unmapped | none | - |
| RV-2 | Execution and Risk Overlay | unmapped | none | - |
| RV-3 | Runtime Integrity and Security | unmapped | none | - |
| RV-4 | Simulation and Ops Flow | unmapped | none | - |
| XR-1 | Short-Cycle Binary Arbitrage Scanner | unmapped | none | - |
| XR-2 | Legging/Execution Safety for Two-Leg Trades | unmapped | none | - |
| XR-3 | Venue Universe and Market-Type Configuration | unmapped | none | - |
| XR-4 | Micro-Edge Throughput Accounting | unmapped | none | - |
| XR-5 | Optional Asymmetric Single-Leg Mode | unmapped | none | - |
| XR-6 | Automation Security Hardening (Linked Setup Thread) | unmapped | none | - |
| XR-7 | Provenance and Confidence Handling | unmapped | none | - |
| HM-1 | Universe-Scale Squeeze Monitoring | unmapped | none | - |
| HM-2 | Multi-Factor Squeeze Feature Set | unmapped | none | - |
| HM-3 | Composite Scoring and Ranking | unmapped | none | - |
| HM-4 | Alerting Pipeline | unmapped | none | - |
| HM-5 | Feature Store and Rolling Snapshot Retention | unmapped | none | - |
| HM-6 | Parameter Tuning and Governance | unmapped | none | - |
| HM-7 | Safety and Promotion Constraints | unmapped | none | - |
| TD-1 | Time-to-Resolution Value Model | unmapped | none | - |
| TD-2 | Hold-vs-Exit Policy Engine | unmapped | none | - |
| TD-3 | Early-Exit Suppression Guard | unmapped | none | - |
| TD-4 | Resolution-Centric Lifecycle Tracking | unmapped | none | - |
| TD-5 | Policy A/B and Promotion Rules | unmapped | none | - |
| TD-6 | Advisory on External Performance Claims | unmapped | none | - |
| ZQ-1 | Split-Plane Architecture (Analysis vs Execution) | unmapped | none | - |
| ZQ-2 | Short-Cycle Feature Evaluation Loop | unmapped | none | - |
| ZQ-3 | Latency and Throughput SLOs for HFT Path | unmapped | none | - |
| ZQ-4 | Kelly-Constrained Position Sizing | unmapped | none | - |
| ZQ-5 | High-Frequency Execution Governance | unmapped | none | - |
| ZQ-6 | Cross-Market Expansion Controls | unmapped | none | - |
| ZQ-7 | Weather/Event-Market Exogenous Data Integration (Optional) | unmapped | none | - |
| ZQ-8 | External Performance Claim Handling | unmapped | none | - |
| KL-1 | Kyle’s Lambda Market-Toxicity Estimation | unmapped | none | - |
| KL-2 | Adverse-Selection Guardrail | unmapped | none | - |
| KL-3 | Impact-Aware Market Selection | unmapped | none | - |
| KL-4 | Microstructure/Fair-Value Divergence Telemetry | unmapped | none | - |
| KL-5 | Execution Diagnostics and SLO Coupling | unmapped | none | - |
| KL-6 | Risk and Promotion Constraints | unmapped | none | - |
| KL-7 | External Claim Handling | unmapped | none | - |
| WF-1 | Wallet-Flow Context Stream | unmapped | none | - |
| WF-2 | Whale Quorum Trigger Logic | unmapped | none | - |
| WF-3 | Pre-Move Entry and Immediate Hedge Workflow | unmapped | none | - |
| WF-4 | Locked-Spread Validation | unmapped | none | - |
| WF-5 | Latency and Reliability Gates for Whale-Flow Strategy | unmapped | none | - |
| WF-6 | Safety and Scope Controls | unmapped | none | - |
| WF-7 | External Claim Handling | unmapped | none | - |
| DV-1 | Strategy-Knowledge Ingestion Pipeline | unmapped | none | - |
| DV-2 | Author-to-Wallet Mapping Layer | unmapped | none | - |
| DV-3 | Publish-vs-Trade Divergence Detection | unmapped | none | - |
| DV-4 | Behavior-Weighted Strategy Overrides | unmapped | none | - |
| DV-5 | Consensus Event Triggering | unmapped | none | - |
| DV-6 | Research-to-Execution Governance | unmapped | none | - |
| DV-7 | Source Reliability and Claim Handling | unmapped | none | - |
| PS-1 | Low-Price Candidate Scanner | unmapped | none | - |
| PS-2 | Basket Campaign Construction | unmapped | none | - |
| PS-3 | Hit-Rate and Expectancy Guardrails | unmapped | none | - |
| PS-4 | High-Volume Settlement and Accounting | unmapped | none | - |
| PS-5 | External Wallet/Bot Signal Hygiene | unmapped | none | - |
| PS-6 | Throughput, Rate-Limit, and Latency Controls | unmapped | none | - |
| PS-7 | Source Reliability and Claim Handling | unmapped | none | - |
| RBI-1 | Research-Backtest-Incubate (RBI) Pipeline | unmapped | none | - |
| RBI-2 | Multi-Agent Role Separation | unmapped | none | - |
| RBI-3 | Parallel Experiment Orchestration | unmapped | none | - |
| RBI-4 | Promotion Gate Before Incubation | unmapped | none | - |
| RBI-5 | Feature/Filter Ablation Requirements | unmapped | none | - |
| RBI-6 | Model Routing, Cost, and Reasoning-Budget Controls | unmapped | none | - |
| RBI-7 | Evaluation Data Breadth and Reproducibility | unmapped | none | - |
| RBI-8 | Source Reliability and Claim Handling | unmapped | none | - |
| CT-1 | Consensus-Over-Single-Wallet Decisioning | unmapped | none | - |
| CT-2 | Wallet Selection and Qualification Filters | unmapped | none | - |
| CT-3 | Wallet Exclusion Heuristics | unmapped | none | - |
| CT-4 | Copy Execution Modes and Controls | unmapped | none | - |
| CT-5 | Ongoing Rotation and Drift Management | unmapped | none | - |
| CT-6 | Portfolio Risk Overlay for Copy Baskets | unmapped | none | - |
| CT-7 | Market Impact and Liquidity Protection | unmapped | none | - |
| CT-8 | Source Reliability and Claim Handling | unmapped | none | - |
| VR-1 | Variance-Drag Measurement Engine | unmapped | none | - |
| VR-2 | Belief-vs-Actual Performance Reconciliation | unmapped | none | - |
| VR-3 | Drawdown and Path-Dependency Diagnostics | unmapped | none | - |
| VR-4 | Risk Calculator Workflow and Latency Targets | unmapped | none | - |
| VR-5 | Reproducible Formula and Code Outputs | unmapped | none | - |
| VR-6 | Data Quality and Metric Integrity Controls | unmapped | none | - |
| VR-7 | Source Reliability and Claim Handling | unmapped | none | - |
| QF-1 | Composite Edge Signal | unmapped | none | - |
| QF-2 | LMSR-Aware Market Modeling | unmapped | none | - |
| QF-3 | Sequential Bayesian Update Loop | unmapped | none | - |
| QF-4 | Explicit EV Entry Gate | unmapped | none | - |
| QF-5 | Fractional Kelly Sizing Policy | unmapped | none | - |
| QF-6 | Strategy Archetype Module Support | unmapped | none | - |
| QF-7 | Publish-vs-Behavior Divergence Mining | unmapped | none | - |
| QF-8 | Live Ops Hub and Sandbox Requirements | unmapped | none | - |
| QF-9 | Source Reliability and Claim Handling | unmapped | none | - |
| HD-1 | Hyperbolic Discount Valuation Path | unmapped | none | - |
| HD-2 | Deterministic Pre-Trade Rule Gate | unmapped | none | - |
| HD-3 | Multi-Stage Agent Workflow | unmapped | none | - |
| HD-4 | Quant Risk Metric Guardrails | unmapped | none | - |
| HD-5 | Arbitrage Consistency Checks | unmapped | none | - |
| HD-6 | Execution Controls and Auto-Hedge | unmapped | none | - |
| HD-7 | Loss-Cause Learning Loop | unmapped | none | - |
| HD-8 | Skill/Prompt Packaging Requirements | unmapped | none | - |
| HD-9 | External Terminal and Paper-Mode Requirements | unmapped | none | - |
| HD-10 | Source Reliability and Claim Handling | unmapped | none | - |
| AR-1 | Fixed-Price Entry Mode | unmapped | none | - |
| AR-2 | Short-Horizon Impulse Capture Logic | unmapped | none | - |
| AR-3 | Aggressive Reinvestment Policy Controls | unmapped | none | - |
| AR-4 | Target-Multiple Exit Framework | unmapped | none | - |
| AR-5 | Compounding Path and Ruin-Risk Analytics | unmapped | none | - |
| AR-6 | Session State, Telemetry, and Control Surface | unmapped | none | - |
| AR-7 | Profile/Wallet Context as Optional Signal | unmapped | none | - |
| AR-8 | Source Reliability and Claim Handling | unmapped | none | - |
| RK-1 | Model Stack and Probability Calibration | unmapped | none | - |
| RK-2 | Explicit Edge Threshold Gate | unmapped | none | - |
| RK-3 | Risk Gate Sequence and Latency Budget | unmapped | none | - |
| RK-4 | Fractional Kelly and Bankroll Caps | unmapped | none | - |
| RK-5 | Hard Risk Limits | unmapped | none | - |
| RK-6 | Signal-Quality and Microstructure Filters | unmapped | none | - |
| RK-7 | Backtest Scoreboard and Category Breakdown | unmapped | none | - |
| RK-8 | Simulated-vs-Live Performance Separation | unmapped | none | - |
| RK-9 | Source Reliability and Claim Handling | unmapped | none | - |
| PH-1 | Market Scope and Timing Window | unmapped | none | - |
| PH-2 | Dual-Leg Parity Entry Rule | unmapped | none | - |
| PH-3 | Hold-to-Resolution Cycle Control | unmapped | none | - |
| PH-4 | Structural-vs-Latency Edge Attribution | unmapped | none | - |
| PH-5 | High-Throughput Reliability Controls | unmapped | none | - |
| PH-6 | Balance-Linked Scaling Guardrails | unmapped | none | - |
| PH-7 | Live Profile Reconciliation and Loss Visibility | unmapped | none | - |
| PH-8 | Copytrade and Third-Party Endpoint Hygiene | unmapped | none | - |
| PH-9 | Deployment and Secret Management Controls | unmapped | none | - |
| PH-10 | Source Reliability and Claim Handling | unmapped | none | - |
| HK-1 | Correlation Decomposition and Hidden Concentration | unmapped | none | - |
| HK-2 | Factor Exposure and Hedge Overlay | unmapped | none | - |
| HK-3 | Boundary-Hit Probability for Near-Resolution Sizing | unmapped | none | - |
| HK-4 | Horizon-Scaling of Uncertainty | unmapped | none | - |
| HK-5 | Volatility Clustering and Shock-Decay Modeling | unmapped | none | - |
| HK-6 | Heteroscedastic Regression and Robust Estimation | unmapped | none | - |
| HK-7 | VaR Ensemble and Assumption Divergence Alerts | unmapped | none | - |
| HK-8 | Martingale/Markov Assumption Boundaries | unmapped | none | - |
| HK-9 | Data-Driven Education/Research Ingestion Governance | unmapped | none | - |
| HK-10 | Source Reliability and Claim Handling | unmapped | none | - |
| AX-1 | Expectancy-First Strategy Evaluation | unmapped | none | - |
| AX-2 | Payoff Asymmetry Guardrails | unmapped | none | - |
| AX-3 | Multi-Model Weather Consensus Gate | unmapped | none | - |
| AX-4 | Forecast-Update Clock Scheduling | unmapped | none | - |
| AX-5 | Stale-Price Capture and Pre-Settlement Exit Rules | unmapped | none | - |
| AX-6 | Regime-Aware Swing Strategy Gating | unmapped | none | - |
| AX-7 | High-Frequency Micro-Bet Controls | unmapped | none | - |
| AX-8 | Data Feed Provenance and Resolution Integrity | unmapped | none | - |
| AX-9 | External Bot and Copytrade Endpoint Hygiene | unmapped | none | - |
| AX-10 | Source Reliability and Claim Handling | unmapped | none | - |
| WK-1 | Market Scope and Horizon Controls | unmapped | none | - |
| WK-2 | Signal Families: Probability Gap and Parity Gap | unmapped | none | - |
| WK-3 | Sequential Probability Update Engine | unmapped | none | - |
| WK-4 | Latency SLO and Execution Pipeline | unmapped | none | - |
| WK-5 | Throughput Reliability and Order-Safety Controls | unmapped | none | - |
| WK-6 | Expected Value and Sizing Discipline | unmapped | none | - |
| WK-7 | Regime-Adaptive Risk Scaling | unmapped | none | - |
| WK-8 | External Prediction Source Governance | unmapped | none | - |
| WK-9 | Public Profile Reconciliation and Tail-Loss Visibility | unmapped | none | - |
| WK-10 | Copytrade Endpoint Hygiene and Claim Handling | unmapped | none | - |
| AL-1 | LMSR Cost Function Fidelity | unmapped | none | - |
| AL-2 | Marginal Price and Probability Coherence | unmapped | none | - |
| AL-3 | Liquidity Parameter (`b`) Governance | unmapped | none | - |
| AL-4 | Trade Impact and Delta-Cost Quoting | unmapped | none | - |
| AL-5 | Bounded-Loss and Subsidy Accounting | unmapped | none | - |
| AL-6 | Inventory State Integrity | unmapped | none | - |
| AL-7 | LMSR-Based Mispricing Detection | unmapped | none | - |
| AL-8 | Liquidity/Counterparty Independence Controls | unmapped | none | - |
| AL-9 | AI-Generated Strategy Artifact Governance | unmapped | none | - |
| AL-10 | Source Reliability and Claim Handling | unmapped | none | - |
| NS-1 | Market-Universe Pre-Filter Gate | unmapped | none | - |
| NS-2 | Ensemble-Confidence Fire Rule | unmapped | none | - |
| NS-3 | Independent Risk-Validator Quorum | unmapped | none | - |
| NS-4 | Parallel Sub-Agent Concurrency Controls | unmapped | none | - |
| NS-5 | Skill Trigger Precision Monitoring for Trading Agents | unmapped | none | - |
| NS-6 | Source Reliability and Claim Handling | unmapped | none | - |
| PL-1 | Weather Distribution-to-Bucket Probability Mapping | unmapped | none | - |
| PL-2 | Paired Entry/Exit Threshold Profile Governance | unmapped | none | - |
| PL-3 | Per-Scan Trade Budget and Market Universe Controls | unmapped | none | - |
| PL-4 | Segregated Execution Wallet and Funding Guardrails | unmapped | none | - |
| PL-5 | Unattended Operation Watchdogs | unmapped | none | - |
| PL-6 | Third-Party Skill/Module Supply-Chain Controls | unmapped | none | - |
| PL-7 | Source Reliability and Claim Handling | unmapped | none | - |
| PG-1 | Wrapper-Fee-Aware Execution Gate | unmapped | none | - |
| PG-2 | Chat-Native Limit Order Lifecycle Controls | unmapped | none | - |
| PG-3 | Bot-Generated Wallet Lifecycle and Recovery Controls | unmapped | none | - |
| PG-4 | Auto-Bridge Deposit Reconciliation | unmapped | none | - |
| PG-5 | Copy-Mirroring Control Plane Hardening | unmapped | none | - |
| PG-6 | Promotional PnL Artifact Separation | unmapped | none | - |
| PG-7 | Source Reliability and Claim Handling | unmapped | none | - |
| HL-1 | Latency-Normalized Opportunity Scoring | unmapped | none | - |
| HL-2 | Micro-Window Execution Integrity | unmapped | none | - |
| HL-3 | Pre-Close Entry Gating | unmapped | none | - |
| HL-4 | Convergence-Exit Automation | unmapped | none | - |
| HL-5 | Feed Lead-Lag Provenance and Entitlement Controls | unmapped | none | - |
| HL-6 | Latency-Edge Capacity and Decay Monitoring | unmapped | none | - |
| HL-7 | Source Reliability and Claim Handling | unmapped | none | - |
| DK-1 | Causal Time-Alignment and Lookahead Prevention | unmapped | none | - |
| DK-2 | Event-Feed Revision and Finality Handling | unmapped | none | - |
| DK-3 | Cross-Domain Latency Baselines and Drift Alerts | unmapped | none | - |
| DK-4 | Source Reliability and Claim Handling | unmapped | none | - |
| WR-1 | Two-Sided Liquidity Provisioning Mode | unmapped | none | - |
| WR-2 | Fill-State Outcome Engine | unmapped | none | - |
| WR-3 | Reward-Aware Net PnL Decomposition | unmapped | none | - |
| WR-4 | One-Leg Fill Hedge Controls | unmapped | none | - |
| WR-5 | Niche-Market Competition Scoring | unmapped | none | - |
| WR-6 | Source Reliability and Claim Handling | unmapped | none | - |
| DN-1 | Social Wallet Address Ingestion and Validation | unmapped | none | - |
| DN-2 | Directed Market-List Trading Mode | unmapped | none | - |
| DN-3 | Preference-Constrained Adaptive Tuning | unmapped | none | - |
| DN-4 | High-Probability Tail-Risk Overlay | unmapped | none | - |
| DN-5 | Source Reliability and Claim Handling | unmapped | none | - |
| SH-1 | Confidence-Ladder Order Slicing | unmapped | none | - |
| SH-2 | Child-Order Sequence Integrity | unmapped | none | - |
| SH-3 | Ultra-Short Horizon Regime Isolation | unmapped | none | - |
| SH-4 | High-Volume Micro-Execution Reliability Budget | unmapped | none | - |
| SH-5 | Source Reliability and Claim Handling | unmapped | none | - |
| RP-1 | Deterministic Metric-Backed Resolution Contracts | unmapped | none | - |
| RP-2 | Verified-Data Oracle and Snapshot Finality | unmapped | none | - |
| RP-3 | Startup/Founder Market Template Library | unmapped | none | - |
| RP-4 | Entity-Centric Market Graph | unmapped | none | - |
| RP-5 | Virtual-Credit Engagement Environment | unmapped | none | - |
| RP-6 | Market Discovery and Coverage Controls | unmapped | none | - |
| RP-7 | Public Activity Feed with Privacy-Safe Telemetry | unmapped | none | - |
| RP-8 | Reputation Leaderboard Quality Controls | unmapped | none | - |
| RP-9 | Source Reliability and Claim Handling | unmapped | none | - |
| GK-1 | One-Command Container Runtime | unmapped | none | - |
| GK-2 | Public Simulation Leaderboard Publication | unmapped | none | - |
| GK-3 | Operator Notification Integrations (Telegram/Discord) | unmapped | none | - |
| GK-4 | Historical Dataset Bootstrap and Seeding | unmapped | none | - |
| GK-5 | Hyperparameter + Purged-CV Automation | unmapped | none | - |
| GK-6 | Automated Monthly Performance Report Builder | unmapped | none | - |
| GK-7 | Strategy Scaffolding and Plugin Extension Interface | unmapped | none | - |
| GK-8 | Hybrid Backtesting Execution Modes | unmapped | none | - |
| GK-9 | Prometheus-Compatible Metrics Surface | unmapped | none | - |
| WA-1 | Primary Backend Framework | unmapped | none | - |
| WA-2 | Primary Frontend Framework | unmapped | none | - |
| WA-3 | Streamlit Role Boundary | unmapped | none | - |
| WA-4 | API and Streaming Contracts | unmapped | none | - |
| WA-5 | Data and Session Architecture | unmapped | none | - |
| WA-6 | AuthN/AuthZ and Security | unmapped | none | - |
| WA-7 | Reliability and Operability | unmapped | none | - |
| WA-8 | Frontend Quality and Testing | unmapped | none | - |
| WA-9 | Migration and Compatibility | unmapped | none | - |
| DXR-1 | Agent Scratchpad Audit Trail | unmapped | none | - |
| DXR-2 | Anti-Loop Tool Execution Controls | unmapped | none | - |
| DXR-3 | Context Overflow Recovery and Memory Flush | unmapped | none | - |
| DXR-4 | Provider-Routed LLM Layer | unmapped | none | - |
| DXR-5 | Conditional Tool Registry and Failover | unmapped | none | - |
| DXR-6 | Skill Package Interface (SKILL.md) | unmapped | none | - |
| DXR-7 | Structured Evaluation Harness | unmapped | none | - |
| DXR-8 | Messaging Channel Gateway with Access Policies | unmapped | none | - |
| WCR-1 | Multi-Source Search Adapter Framework | unmapped | none | - |
| WCR-2 | Recency-Normalized Aggregation | unmapped | none | - |
| WCR-3 | Canonical URL Resolution | unmapped | none | - |
| WCR-4 | Robust JS-Heavy Page Parsing Pipeline | unmapped | none | - |
| WCR-5 | Link Graph Extraction Capability | unmapped | none | - |
| WCR-6 | Resource and Session Controls for Ingestion | unmapped | none | - |
| WCR-7 | Parse Output Quality Contract | unmapped | none | - |
| WCR-8 | Real-Site Integration Test Coverage | unmapped | none | - |
| LLE-1 | Task-Specific Evaluation Packs (Classification + Regression) | unmapped | none | - |
| LLE-2 | Strict Structured Output Contract for Model Judgments | unmapped | none | - |
| LLE-3 | Provider-Parity Tool Calling Layer | unmapped | none | - |
| LLE-4 | Cost and Latency as First-Class Evaluation Metrics | unmapped | none | - |
| LLE-5 | Dual Artifact Output (Metrics + Raw Predictions) | unmapped | none | - |
| LLE-6 | Best-Model Selection per Metric Family | unmapped | none | - |
| LLE-7 | Tolerance-Banded Regression Accuracy | unmapped | none | - |
| LLE-8 | Confusion-Matrix-Native Classification Scoring | unmapped | none | - |
| LLE-9 | Dataset Factory + Local Cache Strategy | unmapped | none | - |
| LLE-10 | Hypothesis-Driven Financial Label Construction | unmapped | none | - |
| LLE-11 | Hierarchical Financial Extraction Workflow (XBRL-Oriented) | unmapped | none | - |
| AHF-1 | Runtime-Composable Agent Graphs | unmapped | none | - |
| AHF-2 | Strategy Flow Templates and Versioned Persistence | unmapped | none | - |
| AHF-3 | Execution Run Registry with Lifecycle Status | unmapped | none | - |
| AHF-4 | Per-Cycle Session Telemetry for Continuous Modes | unmapped | none | - |
| AHF-5 | Server-Sent Event Streaming for Operator UX | unmapped | none | - |
| AHF-6 | Per-Agent Model Routing Overrides | unmapped | none | - |
| AHF-7 | Deterministic Trade Feasibility Pre-Checks | unmapped | none | - |
| AHF-8 | Integrated Long/Short + Margin Accounting Model | unmapped | none | - |
| AHF-9 | Volatility and Correlation-Aware Position Limits | unmapped | none | - |
| AHF-10 | Hybrid Signal Fabric with Reasoning Artifacts | unmapped | none | - |
| AHF-11 | Backtest Progression with Benchmark Context | unmapped | none | - |
| AHF-12 | API Key Vault Operations for Multi-Provider Runtime | unmapped | none | - |
| OBBFD-1 | Deterministic API-Key Resolution Precedence | unmapped | none | - |
| OBBFD-2 | UI-Boot Degraded Mode for Option Endpoints | unmapped | none | - |
| OBBFD-3 | Decorator-Driven Widget Registry Contract | unmapped | none | - |
| OBBFD-4 | Declarative Workspace/App Manifest Endpoint | unmapped | none | - |
| OBBFD-5 | Financial Table Normalization + Transposition Layer | unmapped | none | - |
| OBBFD-6 | Standardized Parameter Options Endpoints | unmapped | none | - |
| OBBFD-7 | Provider Proxy Reliability Envelope | unmapped | none | - |
| OBBFD-8 | Health and Deployment SLO Integration | unmapped | none | - |
| OBBFD-9 | Real-Time Subscription Session Registry (Optional Module) | unmapped | none | - |
| FINQA-1 | Two-Stage Retrieval-to-Reasoning Pipeline Contract | unmapped | none | - |
| FINQA-2 | Unified Multi-Source Evidence Model (Text + Table) | unmapped | none | - |
| FINQA-3 | Retrieval Quality Metrics with Top-K Recall Reporting | unmapped | none | - |
| FINQA-4 | Context Packing Under Token/Length Budgets | unmapped | none | - |
| FINQA-5 | Executable Program DSL for Numeric Reasoning | unmapped | none | - |
| FINQA-6 | Dual Accuracy Regime: Execution vs Program Equivalence | unmapped | none | - |
| FINQA-7 | Blind-Test Benchmark Governance | unmapped | none | - |
| FINQA-8 | Leakage-Resistant Data Transformation Controls | unmapped | none | - |
| FINQA-9 | Program Representation Compatibility (Sequential + Nested) | unmapped | none | - |
| FINQA-10 | Prediction Artifact Standardization for External Leaderboards | unmapped | none | - |
| PMDESK-1 | Layered Desk Runtime Separation | unmapped | none | - |
| PMDESK-2 | Bayesian Probability Update Engine | unmapped | none | - |
| PMDESK-3 | Cross-Market Dependency Graph Enforcement | unmapped | none | - |
| PMDESK-4 | Calibration Surface and Bias Diagnostics | unmapped | none | - |
| PMDESK-5 | Uncertainty-Adjusted Kelly Sizing | unmapped | none | - |
| PMDESK-6 | Microstructure-Aware Execution Algorithms | unmapped | none | - |
| PMDESK-7 | Informed-Flow and Liquidity Kill Switches | unmapped | none | - |
| PMDESK-8 | Portfolio Risk Guardrails (VaR + Drawdown) | unmapped | none | - |
| PMDESK-9 | Cross-Venue Price Discovery and Latency Arb Module | unmapped | none | - |
| PMDESK-10 | On-Chain Settlement-Aware Monitoring | unmapped | none | - |
| PMDESK-11 | Event-Driven Data Backbone Requirements | unmapped | none | - |
| PMDESK-12 | Infrastructure and Reliability Baseline | unmapped | none | - |
| FAUI-1 | Tool-Aware Generative UI Rendering Contract | unmapped | none | - |
| FAUI-2 | Stream-Event-Driven Chat Orchestration | unmapped | none | - |
| FAUI-3 | Remote Runnable API Boundary | unmapped | none | - |
| FAUI-4 | Graph Node Event Contract Stability | unmapped | none | - |
| FAUI-5 | Strongly Typed Tool Argument Schemas | unmapped | none | - |
| FAUI-6 | Multi-Source Financial + Web Retrieval Surface | unmapped | none | - |
| FAUI-7 | UI-Native Data Shape Normalization | unmapped | none | - |
| FAUI-8 | Progressive Loading Components per Tool Type | unmapped | none | - |
| FAUI-9 | Structured Error Envelope for Tool Failures | unmapped | none | - |
| FAUI-10 | Frontend/Backend Local Compose Development Contract | unmapped | none | - |
| FAUI-11 | Agent Run Observability and Trace Correlation | unmapped | none | - |
| FAUI-12 | Extensible Tool-and-Component Plugin Path | unmapped | none | - |
| FDATA-1 | Multi-Source Financial Corpus Ingestion | unmapped | none | - |
| FDATA-2 | SEC Filing Identity + Access Compliance | unmapped | none | - |
| FDATA-3 | Filing Item-Scoped Extraction Controls | unmapped | none | - |
| FDATA-4 | Deterministic Text Cleanup Pipeline | unmapped | none | - |
| FDATA-5 | Token-Aware Chunking with Overlap | unmapped | none | - |
| FDATA-6 | Question Budget Allocation Policy | unmapped | none | - |
| FDATA-7 | Structured LLM Function-Call Output Contract | unmapped | none | - |
| FDATA-8 | Grounded, Standalone Q/A Quality Policy | unmapped | none | - |
| FDATA-9 | Provider Guardrails and Retry Strategy | unmapped | none | - |
| FDATA-10 | Canonical Dataset Schema and Validation | unmapped | none | - |
| FDATA-11 | Generation Provenance and Usage Telemetry | unmapped | none | - |
| FDATA-12 | Synthetic Financial QA Regression Tests | unmapped | none | - |
| FINGEN-1 | Server-Action AI Runtime with Split UI/Model State | unmapped | none | - |
| FINGEN-2 | Optimistic User-Turn Rendering | unmapped | none | - |
| FINGEN-3 | Unified Event Stream Handling for LLM + Tools | unmapped | none | - |
| FINGEN-4 | Tool Invocation Transparency UI | unmapped | none | - |
| FINGEN-5 | Tool-Result-to-Widget Routing | unmapped | none | - |
| FINGEN-6 | Financial Data Adapter Layer (Polygon-Style) | unmapped | none | - |
| FINGEN-7 | Structured Tool Schemas for Agent Reliability | unmapped | none | - |
| FINGEN-8 | Message-Role Conversion Contract | unmapped | none | - |
| FINGEN-9 | Rich Markdown Rendering with Data-Oriented Components | unmapped | none | - |
| FINGEN-10 | Input UX Controls for High-Velocity Chat | unmapped | none | - |
| FINGEN-11 | Scroll Anchoring and Navigation in Streaming Chats | unmapped | none | - |
| FINGEN-12 | Multi-Modal Assistant Turn Composition | unmapped | none | - |
| SECAPI-1 | SEC-Compliant Request Identity Policy | unmapped | none | - |
| SECAPI-2 | Master Ticker-to-CIK Registry Ingestion | unmapped | none | - |
| SECAPI-3 | Canonical CIK Normalization Contract | unmapped | none | - |
| SECAPI-4 | Company Submissions Metadata Pipeline | unmapped | none | - |
| SECAPI-5 | XBRL Company Facts Taxonomy Traversal | unmapped | none | - |
| SECAPI-6 | Concept-Level Time-Series Endpoint Support | unmapped | none | - |
| SECAPI-7 | Unit-Aware Metric Extraction | unmapped | none | - |
| SECAPI-8 | Form-Scoped Series Derivation | unmapped | none | - |
| SECAPI-9 | Tabular Normalization for Analytics Pipelines | unmapped | none | - |
| SECAPI-10 | Issuer Fundamentals Discovery Utilities | unmapped | none | - |
| TVSRC-1 | Public Indicator-Script Ingestion Contract | unmapped | none | - |
| TVSRC-2 | Pine-to-Python Translation Pipeline | unmapped | none | - |
| TVSRC-3 | Translation Equivalence Validation | unmapped | none | - |
| TVSRC-4 | Batch Backtest Factory for Large Candidate Sets | unmapped | none | - |
| TVSRC-5 | Filter-Augmented Variant Expansion and Ablation | unmapped | none | - |
| TVSRC-6 | Composite-Score Ranking from Results Registry | unmapped | none | - |
| TVSRC-7 | Short-Side Exit Logic Invariant Tests | unmapped | none | - |
| TVSRC-8 | Coverage Pipeline for Trending/Editor-Pick Script Sources | unmapped | none | - |
| TVSRC-9 | Source Reliability and Claim Handling | unmapped | none | - |
| COMP-1 | Documentation Availability and Metadata Integrity | implemented | done | docs/COMP_ISSUES_DRAFT.md, docs/TODO.md, scripts/create_comp_issues.sh |
| COMP-2 | Semantic Release and Distribution Credibility | implemented | done | docs/COMP_ISSUES_DRAFT.md, docs/TODO.md |
| COMP-3 | Public Benchmark Quality Gate | implemented | done | docs/COMP_ISSUES_DRAFT.md, docs/TODO.md |
| COMP-4 | Golden Dataset and Provenance Governance | implemented | done | docs/COMP_ISSUES_DRAFT.md, docs/TODO.md |
| COMP-5 | Reference Strategy Pack Publication Standard | implemented | done | docs/COMP_ISSUES_DRAFT.md, docs/TODO.md |
| COMP-6 | One Engine, Two Product Surfaces | implemented | done | docs/COMP_ISSUES_DRAFT.md, docs/TODO.md |
| COMP-7 | Studio (Casual) UX Contract | planned | open | docs/COMP_ISSUES_DRAFT.md, docs/TODO.md |
| COMP-8 | Core (Professional) UX Contract | planned | open | docs/COMP_ISSUES_DRAFT.md, docs/TODO.md |
| COMP-9 | Surface Parity and Traceability | implemented | done | docs/COMP_ISSUES_DRAFT.md, docs/TODO.md |
| COMP-10 | Wedge-First Market Scope Governance | planned | open | docs/COMP_ISSUES_DRAFT.md, docs/TODO.md |
| COMP-11 | First-Success CLI Path | implemented | done | docs/COMP_ISSUES_DRAFT.md, docs/TODO.md |
| COMP-12 | Template-First, Code-Optional, Code-Visible Operation | traced | none | docs/COMP_ISSUES_DRAFT.md, docs/TODO.md |
| COMP-13 | Public Claim and Evidence Policy | implemented | done | docs/COMP_ISSUES_DRAFT.md, docs/TODO.md |
| COMP-14 | Tiering Model Safety Baseline | planned | open | docs/COMP_ISSUES_DRAFT.md, docs/TODO.md, scripts/create_comp_issues.sh |
| LANG-1 | Python-First, Not Python-Only Architecture Policy | unmapped | none | - |
| LANG-2 | Native Kernel Boundary for Hot Path | implemented | done | docs/TODO.md |
| LANG-3 | Native Migration Trigger Criteria | partial | partial | docs/TODO.md |
| LANG-4 | Research Data Plane Standard | implemented | done | docs/TODO.md |
| LANG-5 | API and Configuration Contract Hardening | implemented | done | docs/TODO.md |
| LANG-6 | UI Surface Coherence Requirement | partial | partial | docs/TODO.md |
| LANG-7 | FastAPI-Centered Control Plane | implemented | done | docs/TODO.md |
| LANG-8 | Storage-Tier Policy | implemented | done | docs/TODO.md |
| LANG-9 | Engine-Loop and Dashboard Responsiveness SLOs | implemented | done | docs/TODO.md |
| LANG-10 | Interop Packaging and Distribution | implemented | done | docs/TODO.md |
| LANG-11 | UI Migration Safety | implemented | done | docs/TODO.md |
| LANG-12 | Source Reliability and Claim Handling | unmapped | none | - |
| PMKT-1 | Official Integration Index | implemented | done | docs/TODO.md, tests/test_generate_srs_gap_backlog_tool.py |
| PMKT-2 | Auth State Segmentation for Venue Clients | implemented | done | docs/TODO.md |
| PMKT-3 | Signature-Type and Funder Address Contract | implemented | done | docs/TODO.md |
| PMKT-4 | API Credential Lifecycle and Rotation | implemented | done | docs/TODO.md |
| PMKT-5 | Allowance and Approval Preflight Controls | implemented | done | docs/TODO.md |
| PMKT-6 | Canonical Order Lifecycle and Batch Operations | implemented | done | docs/TODO.md |
| PMKT-7 | Streaming Coverage and Disconnect Safety | implemented | done | .github/workflows/ci.yml, docs/TODO.md |
| PMKT-8 | Remote Signer and Builder-Mode Support | implemented | done | docs/TODO.md |
| PMKT-9 | CLI Automation Contract | implemented | done | docs/TODO.md |
| PMKT-10 | Read-Only First and Guided Setup UX | implemented | done | docs/TODO.md |
| PMKT-11 | Wallet-Mode Example Packs and Smoke Tests | implemented | done | docs/TODO.md |
| PMKT-12 | Hybrid Matching and Non-Custodial Settlement Invariants | implemented | done | docs/TODO.md |
| PMKT-13 | Complementary-Outcome Fee Symmetry | implemented | done | docs/TODO.md |
| PMKT-14 | Deployment Registry and Audit Artifact Governance | implemented | done | docs/TODO.md |
| PMKT-15 | Source Reliability and Claim Handling | unmapped | none | - |
| MOAT-1 | Per-Order Truth Graph | implemented | done | docs/TODO.md |
| MOAT-2 | Live Divergence Diagnosis and Prescriptive Actions | implemented | done | docs/TODO.md |
| MOAT-3 | Promotion OS State Machine | implemented | done | docs/TODO.md |
| MOAT-4 | Promotion Memo and Rollback Contract | implemented | done | docs/TODO.md |
| MOAT-5 | Stage-Aware Capital Allocation | implemented | done | docs/TODO.md |
| MOAT-6 | Execution Intelligence Data Model | implemented | done | docs/TODO.md |
| MOAT-7 | Adaptive Routing and Throttling from Execution Intelligence | implemented | done | docs/TODO.md |
| MOAT-8 | Single Strategy Object Across Casual and Pro Surfaces | partial | partial | docs/TODO.md |
| MOAT-9 | Bidirectional Transparency and Parity | implemented | done | docs/TODO.md |
| MOAT-10 | Policy-Constrained Autonomous Operator | implemented | done | docs/TODO.md |
| MOAT-11 | Incident Co-Pilot and Safe Rollback Assist | implemented | done | docs/TODO.md |
| MOAT-12 | Proof-as-Product Artifact Pipeline | implemented | done | docs/TODO.md |
| MOAT-13 | Public Trust Classifications and Evidence Gates | partial | partial | docs/TODO.md |
| MOAT-14 | Team Governance and Capital Controls | implemented | done | docs/TODO.md |
| MOAT-15 | Moat-vs-Parity Roadmap Governance | partial | partial | docs/TODO.md |
| MOAT-16 | Source Reliability and Claim Handling | implemented | done | docs/TODO.md |
