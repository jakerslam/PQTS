# SRS Gap Backlog

Auto-generated from SRS coverage. Non-implemented requirements are grouped by priority.

## P0

Count: **24**

| ID | Prefix | Status | Requirement |
|---|---|---|---|
| AC-1 | AC | unmapped | Backtest Readiness |
| AC-2 | AC | unmapped | Paper-Trade Readiness |
| AC-3 | AC | unmapped | Promotion Gate |
| BF-1 | BF | unmapped | Runtime Configuration and Boot Controls |
| BF-2 | BF | unmapped | Market/Strategy Control Plane |
| BF-3 | BF | unmapped | Mandatory Order and Risk Pipeline |
| BF-4 | BF | unmapped | Market Data and Reliability Controls |
| BF-5 | BF | unmapped | Research, Simulation, and Ops Automation |
| BF-6 | BF | unmapped | Security, Compliance, and Data Governance |
| FR-1 | FR | unmapped | Market Probability Normalization |
| FR-2 | FR | unmapped | Fair Probability Estimation |
| FR-3 | FR | unmapped | Underdog Mispricing Signal |
| FR-4 | FR | unmapped | Profitability Gate Integration |
| FR-5 | FR | unmapped | Position Sizing |
| FR-6 | FR | unmapped | Portfolio Constraints |
| FR-7 | FR | unmapped | Exit and Lifecycle Rules |
| FR-8 | FR | unmapped | Telemetry and Attribution |
| NFR-1 | NFR | unmapped | Latency |
| NFR-2 | NFR | unmapped | Reliability |
| NFR-3 | NFR | unmapped | Determinism |
| RV-1 | RV | unmapped | Core Control Plane |
| RV-2 | RV | unmapped | Execution and Risk Overlay |
| RV-3 | RV | unmapped | Runtime Integrity and Security |
| RV-4 | RV | unmapped | Simulation and Ops Flow |

## P1

Count: **24**

| ID | Prefix | Status | Requirement |
|---|---|---|---|
| COMP-10 | COMP | partial | Wedge-First Market Scope Governance |
| COMP-14 | COMP | partial | Tiering Model Safety Baseline |
| COMP-7 | COMP | partial | Studio (Casual) UX Contract |
| COMP-8 | COMP | partial | Core (Professional) UX Contract |
| LANG-3 | LANG | partial | Native Migration Trigger Criteria |
| LANG-6 | LANG | partial | UI Surface Coherence Requirement |
| MOAT-13 | MOAT | partial | Public Trust Classifications and Evidence Gates |
| MOAT-15 | MOAT | partial | Moat-vs-Parity Roadmap Governance |
| MOAT-8 | MOAT | partial | Single Strategy Object Across Casual and Pro Surfaces |
| XR-1 | XR | unmapped | Short-Cycle Binary Arbitrage Scanner |
| XR-2 | XR | unmapped | Legging/Execution Safety for Two-Leg Trades |
| XR-3 | XR | unmapped | Venue Universe and Market-Type Configuration |
| XR-4 | XR | unmapped | Micro-Edge Throughput Accounting |
| XR-5 | XR | unmapped | Optional Asymmetric Single-Leg Mode |
| XR-6 | XR | unmapped | Automation Security Hardening (Linked Setup Thread) |
| XR-7 | XR | unmapped | Provenance and Confidence Handling |
| ZQ-1 | ZQ | unmapped | Split-Plane Architecture (Analysis vs Execution) |
| ZQ-2 | ZQ | unmapped | Short-Cycle Feature Evaluation Loop |
| ZQ-3 | ZQ | unmapped | Latency and Throughput SLOs for HFT Path |
| ZQ-4 | ZQ | unmapped | Kelly-Constrained Position Sizing |
| ZQ-5 | ZQ | unmapped | High-Frequency Execution Governance |
| ZQ-6 | ZQ | unmapped | Cross-Market Expansion Controls |
| ZQ-7 | ZQ | unmapped | Weather/Event-Market Exogenous Data Integration (Optional) |
| ZQ-8 | ZQ | unmapped | External Performance Claim Handling |

## P2

Count: **349**

| ID | Prefix | Status | Requirement |
|---|---|---|---|
| AHF-1 | AHF | unmapped | Runtime-Composable Agent Graphs |
| AHF-10 | AHF | unmapped | Hybrid Signal Fabric with Reasoning Artifacts |
| AHF-11 | AHF | unmapped | Backtest Progression with Benchmark Context |
| AHF-12 | AHF | unmapped | API Key Vault Operations for Multi-Provider Runtime |
| AHF-2 | AHF | unmapped | Strategy Flow Templates and Versioned Persistence |
| AHF-3 | AHF | unmapped | Execution Run Registry with Lifecycle Status |
| AHF-4 | AHF | unmapped | Per-Cycle Session Telemetry for Continuous Modes |
| AHF-5 | AHF | unmapped | Server-Sent Event Streaming for Operator UX |
| AHF-6 | AHF | unmapped | Per-Agent Model Routing Overrides |
| AHF-7 | AHF | unmapped | Deterministic Trade Feasibility Pre-Checks |
| AHF-8 | AHF | unmapped | Integrated Long/Short + Margin Accounting Model |
| AHF-9 | AHF | unmapped | Volatility and Correlation-Aware Position Limits |
| AL-1 | AL | unmapped | LMSR Cost Function Fidelity |
| AL-10 | AL | unmapped | Source Reliability and Claim Handling |
| AL-2 | AL | unmapped | Marginal Price and Probability Coherence |
| AL-3 | AL | unmapped | Liquidity Parameter (`b`) Governance |
| AL-4 | AL | unmapped | Trade Impact and Delta-Cost Quoting |
| AL-5 | AL | unmapped | Bounded-Loss and Subsidy Accounting |
| AL-6 | AL | unmapped | Inventory State Integrity |
| AL-7 | AL | unmapped | LMSR-Based Mispricing Detection |
| AL-8 | AL | unmapped | Liquidity/Counterparty Independence Controls |
| AL-9 | AL | unmapped | AI-Generated Strategy Artifact Governance |
| AR-1 | AR | unmapped | Fixed-Price Entry Mode |
| AR-2 | AR | unmapped | Short-Horizon Impulse Capture Logic |
| AR-3 | AR | unmapped | Aggressive Reinvestment Policy Controls |
| AR-4 | AR | unmapped | Target-Multiple Exit Framework |
| AR-5 | AR | unmapped | Compounding Path and Ruin-Risk Analytics |
| AR-6 | AR | unmapped | Session State, Telemetry, and Control Surface |
| AR-7 | AR | unmapped | Profile/Wallet Context as Optional Signal |
| AR-8 | AR | unmapped | Source Reliability and Claim Handling |
| AX-1 | AX | unmapped | Expectancy-First Strategy Evaluation |
| AX-10 | AX | unmapped | Source Reliability and Claim Handling |
| AX-2 | AX | unmapped | Payoff Asymmetry Guardrails |
| AX-3 | AX | unmapped | Multi-Model Weather Consensus Gate |
| AX-4 | AX | unmapped | Forecast-Update Clock Scheduling |
| AX-5 | AX | unmapped | Stale-Price Capture and Pre-Settlement Exit Rules |
| AX-6 | AX | unmapped | Regime-Aware Swing Strategy Gating |
| AX-7 | AX | unmapped | High-Frequency Micro-Bet Controls |
| AX-8 | AX | unmapped | Data Feed Provenance and Resolution Integrity |
| AX-9 | AX | unmapped | External Bot and Copytrade Endpoint Hygiene |
| CT-1 | CT | unmapped | Consensus-Over-Single-Wallet Decisioning |
| CT-2 | CT | unmapped | Wallet Selection and Qualification Filters |
| CT-3 | CT | unmapped | Wallet Exclusion Heuristics |
| CT-4 | CT | unmapped | Copy Execution Modes and Controls |
| CT-5 | CT | unmapped | Ongoing Rotation and Drift Management |
| CT-6 | CT | unmapped | Portfolio Risk Overlay for Copy Baskets |
| CT-7 | CT | unmapped | Market Impact and Liquidity Protection |
| CT-8 | CT | unmapped | Source Reliability and Claim Handling |
| DK-1 | DK | unmapped | Causal Time-Alignment and Lookahead Prevention |
| DK-2 | DK | unmapped | Event-Feed Revision and Finality Handling |
| DK-3 | DK | unmapped | Cross-Domain Latency Baselines and Drift Alerts |
| DK-4 | DK | unmapped | Source Reliability and Claim Handling |
| DN-1 | DN | unmapped | Social Wallet Address Ingestion and Validation |
| DN-2 | DN | unmapped | Directed Market-List Trading Mode |
| DN-3 | DN | unmapped | Preference-Constrained Adaptive Tuning |
| DN-4 | DN | unmapped | High-Probability Tail-Risk Overlay |
| DN-5 | DN | unmapped | Source Reliability and Claim Handling |
| DV-1 | DV | unmapped | Strategy-Knowledge Ingestion Pipeline |
| DV-2 | DV | unmapped | Author-to-Wallet Mapping Layer |
| DV-3 | DV | unmapped | Publish-vs-Trade Divergence Detection |
| DV-4 | DV | unmapped | Behavior-Weighted Strategy Overrides |
| DV-5 | DV | unmapped | Consensus Event Triggering |
| DV-6 | DV | unmapped | Research-to-Execution Governance |
| DV-7 | DV | unmapped | Source Reliability and Claim Handling |
| DXR-1 | DXR | unmapped | Agent Scratchpad Audit Trail |
| DXR-2 | DXR | unmapped | Anti-Loop Tool Execution Controls |
| DXR-3 | DXR | unmapped | Context Overflow Recovery and Memory Flush |
| DXR-4 | DXR | unmapped | Provider-Routed LLM Layer |
| DXR-5 | DXR | unmapped | Conditional Tool Registry and Failover |
| DXR-6 | DXR | unmapped | Skill Package Interface (SKILL.md) |
| DXR-7 | DXR | unmapped | Structured Evaluation Harness |
| DXR-8 | DXR | unmapped | Messaging Channel Gateway with Access Policies |
| FAUI-1 | FAUI | unmapped | Tool-Aware Generative UI Rendering Contract |
| FAUI-10 | FAUI | unmapped | Frontend/Backend Local Compose Development Contract |
| FAUI-11 | FAUI | unmapped | Agent Run Observability and Trace Correlation |
| FAUI-12 | FAUI | unmapped | Extensible Tool-and-Component Plugin Path |
| FAUI-2 | FAUI | unmapped | Stream-Event-Driven Chat Orchestration |
| FAUI-3 | FAUI | unmapped | Remote Runnable API Boundary |
| FAUI-4 | FAUI | unmapped | Graph Node Event Contract Stability |
| FAUI-5 | FAUI | unmapped | Strongly Typed Tool Argument Schemas |
| FAUI-6 | FAUI | unmapped | Multi-Source Financial + Web Retrieval Surface |
| FAUI-7 | FAUI | unmapped | UI-Native Data Shape Normalization |
| FAUI-8 | FAUI | unmapped | Progressive Loading Components per Tool Type |
| FAUI-9 | FAUI | unmapped | Structured Error Envelope for Tool Failures |
| FDATA-1 | FDATA | unmapped | Multi-Source Financial Corpus Ingestion |
| FDATA-10 | FDATA | unmapped | Canonical Dataset Schema and Validation |
| FDATA-11 | FDATA | unmapped | Generation Provenance and Usage Telemetry |
| FDATA-12 | FDATA | unmapped | Synthetic Financial QA Regression Tests |
| FDATA-2 | FDATA | unmapped | SEC Filing Identity + Access Compliance |
| FDATA-3 | FDATA | unmapped | Filing Item-Scoped Extraction Controls |
| FDATA-4 | FDATA | unmapped | Deterministic Text Cleanup Pipeline |
| FDATA-5 | FDATA | unmapped | Token-Aware Chunking with Overlap |
| FDATA-6 | FDATA | unmapped | Question Budget Allocation Policy |
| FDATA-7 | FDATA | unmapped | Structured LLM Function-Call Output Contract |
| FDATA-8 | FDATA | unmapped | Grounded, Standalone Q/A Quality Policy |
| FDATA-9 | FDATA | unmapped | Provider Guardrails and Retry Strategy |
| FINGEN-1 | FINGEN | unmapped | Server-Action AI Runtime with Split UI/Model State |
| FINGEN-10 | FINGEN | unmapped | Input UX Controls for High-Velocity Chat |
| FINGEN-11 | FINGEN | unmapped | Scroll Anchoring and Navigation in Streaming Chats |
| FINGEN-12 | FINGEN | unmapped | Multi-Modal Assistant Turn Composition |
| FINGEN-2 | FINGEN | unmapped | Optimistic User-Turn Rendering |
| FINGEN-3 | FINGEN | unmapped | Unified Event Stream Handling for LLM + Tools |
| FINGEN-4 | FINGEN | unmapped | Tool Invocation Transparency UI |
| FINGEN-5 | FINGEN | unmapped | Tool-Result-to-Widget Routing |
| FINGEN-6 | FINGEN | unmapped | Financial Data Adapter Layer (Polygon-Style) |
| FINGEN-7 | FINGEN | unmapped | Structured Tool Schemas for Agent Reliability |
| FINGEN-8 | FINGEN | unmapped | Message-Role Conversion Contract |
| FINGEN-9 | FINGEN | unmapped | Rich Markdown Rendering with Data-Oriented Components |
| FINQA-1 | FINQA | unmapped | Two-Stage Retrieval-to-Reasoning Pipeline Contract |
| FINQA-10 | FINQA | unmapped | Prediction Artifact Standardization for External Leaderboards |
| FINQA-2 | FINQA | unmapped | Unified Multi-Source Evidence Model (Text + Table) |
| FINQA-3 | FINQA | unmapped | Retrieval Quality Metrics with Top-K Recall Reporting |
| FINQA-4 | FINQA | unmapped | Context Packing Under Token/Length Budgets |
| FINQA-5 | FINQA | unmapped | Executable Program DSL for Numeric Reasoning |
| FINQA-6 | FINQA | unmapped | Dual Accuracy Regime: Execution vs Program Equivalence |
| FINQA-7 | FINQA | unmapped | Blind-Test Benchmark Governance |
| FINQA-8 | FINQA | unmapped | Leakage-Resistant Data Transformation Controls |
| FINQA-9 | FINQA | unmapped | Program Representation Compatibility (Sequential + Nested) |
| GK-1 | GK | unmapped | One-Command Container Runtime |
| GK-2 | GK | unmapped | Public Simulation Leaderboard Publication |
| GK-3 | GK | unmapped | Operator Notification Integrations (Telegram/Discord) |
| GK-4 | GK | unmapped | Historical Dataset Bootstrap and Seeding |
| GK-5 | GK | unmapped | Hyperparameter + Purged-CV Automation |
| GK-6 | GK | unmapped | Automated Monthly Performance Report Builder |
| GK-7 | GK | unmapped | Strategy Scaffolding and Plugin Extension Interface |
| GK-8 | GK | unmapped | Hybrid Backtesting Execution Modes |
| GK-9 | GK | unmapped | Prometheus-Compatible Metrics Surface |
| HD-1 | HD | unmapped | Hyperbolic Discount Valuation Path |
| HD-10 | HD | unmapped | Source Reliability and Claim Handling |
| HD-2 | HD | unmapped | Deterministic Pre-Trade Rule Gate |
| HD-3 | HD | unmapped | Multi-Stage Agent Workflow |
| HD-4 | HD | unmapped | Quant Risk Metric Guardrails |
| HD-5 | HD | unmapped | Arbitrage Consistency Checks |
| HD-6 | HD | unmapped | Execution Controls and Auto-Hedge |
| HD-7 | HD | unmapped | Loss-Cause Learning Loop |
| HD-8 | HD | unmapped | Skill/Prompt Packaging Requirements |
| HD-9 | HD | unmapped | External Terminal and Paper-Mode Requirements |
| HK-1 | HK | unmapped | Correlation Decomposition and Hidden Concentration |
| HK-10 | HK | unmapped | Source Reliability and Claim Handling |
| HK-2 | HK | unmapped | Factor Exposure and Hedge Overlay |
| HK-3 | HK | unmapped | Boundary-Hit Probability for Near-Resolution Sizing |
| HK-4 | HK | unmapped | Horizon-Scaling of Uncertainty |
| HK-5 | HK | unmapped | Volatility Clustering and Shock-Decay Modeling |
| HK-6 | HK | unmapped | Heteroscedastic Regression and Robust Estimation |
| HK-7 | HK | unmapped | VaR Ensemble and Assumption Divergence Alerts |
| HK-8 | HK | unmapped | Martingale/Markov Assumption Boundaries |
| HK-9 | HK | unmapped | Data-Driven Education/Research Ingestion Governance |
| HL-1 | HL | unmapped | Latency-Normalized Opportunity Scoring |
| HL-2 | HL | unmapped | Micro-Window Execution Integrity |
| HL-3 | HL | unmapped | Pre-Close Entry Gating |
| HL-4 | HL | unmapped | Convergence-Exit Automation |
| HL-5 | HL | unmapped | Feed Lead-Lag Provenance and Entitlement Controls |
| HL-6 | HL | unmapped | Latency-Edge Capacity and Decay Monitoring |
| HL-7 | HL | unmapped | Source Reliability and Claim Handling |
| HM-1 | HM | unmapped | Universe-Scale Squeeze Monitoring |
| HM-2 | HM | unmapped | Multi-Factor Squeeze Feature Set |
| HM-3 | HM | unmapped | Composite Scoring and Ranking |
| HM-4 | HM | unmapped | Alerting Pipeline |
| HM-5 | HM | unmapped | Feature Store and Rolling Snapshot Retention |
| HM-6 | HM | unmapped | Parameter Tuning and Governance |
| HM-7 | HM | unmapped | Safety and Promotion Constraints |
| KL-1 | KL | unmapped | Kyle’s Lambda Market-Toxicity Estimation |
| KL-2 | KL | unmapped | Adverse-Selection Guardrail |
| KL-3 | KL | unmapped | Impact-Aware Market Selection |
| KL-4 | KL | unmapped | Microstructure/Fair-Value Divergence Telemetry |
| KL-5 | KL | unmapped | Execution Diagnostics and SLO Coupling |
| KL-6 | KL | unmapped | Risk and Promotion Constraints |
| KL-7 | KL | unmapped | External Claim Handling |
| LLE-1 | LLE | unmapped | Task-Specific Evaluation Packs (Classification + Regression) |
| LLE-10 | LLE | unmapped | Hypothesis-Driven Financial Label Construction |
| LLE-11 | LLE | unmapped | Hierarchical Financial Extraction Workflow (XBRL-Oriented) |
| LLE-2 | LLE | unmapped | Strict Structured Output Contract for Model Judgments |
| LLE-3 | LLE | unmapped | Provider-Parity Tool Calling Layer |
| LLE-4 | LLE | unmapped | Cost and Latency as First-Class Evaluation Metrics |
| LLE-5 | LLE | unmapped | Dual Artifact Output (Metrics + Raw Predictions) |
| LLE-6 | LLE | unmapped | Best-Model Selection per Metric Family |
| LLE-7 | LLE | unmapped | Tolerance-Banded Regression Accuracy |
| LLE-8 | LLE | unmapped | Confusion-Matrix-Native Classification Scoring |
| LLE-9 | LLE | unmapped | Dataset Factory + Local Cache Strategy |
| NS-1 | NS | unmapped | Market-Universe Pre-Filter Gate |
| NS-2 | NS | unmapped | Ensemble-Confidence Fire Rule |
| NS-3 | NS | unmapped | Independent Risk-Validator Quorum |
| NS-4 | NS | unmapped | Parallel Sub-Agent Concurrency Controls |
| NS-5 | NS | unmapped | Skill Trigger Precision Monitoring for Trading Agents |
| NS-6 | NS | unmapped | Source Reliability and Claim Handling |
| OBBFD-1 | OBBFD | unmapped | Deterministic API-Key Resolution Precedence |
| OBBFD-2 | OBBFD | unmapped | UI-Boot Degraded Mode for Option Endpoints |
| OBBFD-3 | OBBFD | unmapped | Decorator-Driven Widget Registry Contract |
| OBBFD-4 | OBBFD | unmapped | Declarative Workspace/App Manifest Endpoint |
| OBBFD-5 | OBBFD | unmapped | Financial Table Normalization + Transposition Layer |
| OBBFD-6 | OBBFD | unmapped | Standardized Parameter Options Endpoints |
| OBBFD-7 | OBBFD | unmapped | Provider Proxy Reliability Envelope |
| OBBFD-8 | OBBFD | unmapped | Health and Deployment SLO Integration |
| OBBFD-9 | OBBFD | unmapped | Real-Time Subscription Session Registry (Optional Module) |
| PG-1 | PG | unmapped | Wrapper-Fee-Aware Execution Gate |
| PG-2 | PG | unmapped | Chat-Native Limit Order Lifecycle Controls |
| PG-3 | PG | unmapped | Bot-Generated Wallet Lifecycle and Recovery Controls |
| PG-4 | PG | unmapped | Auto-Bridge Deposit Reconciliation |
| PG-5 | PG | unmapped | Copy-Mirroring Control Plane Hardening |
| PG-6 | PG | unmapped | Promotional PnL Artifact Separation |
| PG-7 | PG | unmapped | Source Reliability and Claim Handling |
| PH-1 | PH | unmapped | Market Scope and Timing Window |
| PH-10 | PH | unmapped | Source Reliability and Claim Handling |
| PH-2 | PH | unmapped | Dual-Leg Parity Entry Rule |
| PH-3 | PH | unmapped | Hold-to-Resolution Cycle Control |
| PH-4 | PH | unmapped | Structural-vs-Latency Edge Attribution |
| PH-5 | PH | unmapped | High-Throughput Reliability Controls |
| PH-6 | PH | unmapped | Balance-Linked Scaling Guardrails |
| PH-7 | PH | unmapped | Live Profile Reconciliation and Loss Visibility |
| PH-8 | PH | unmapped | Copytrade and Third-Party Endpoint Hygiene |
| PH-9 | PH | unmapped | Deployment and Secret Management Controls |
| PL-1 | PL | unmapped | Weather Distribution-to-Bucket Probability Mapping |
| PL-2 | PL | unmapped | Paired Entry/Exit Threshold Profile Governance |
| PL-3 | PL | unmapped | Per-Scan Trade Budget and Market Universe Controls |
| PL-4 | PL | unmapped | Segregated Execution Wallet and Funding Guardrails |
| PL-5 | PL | unmapped | Unattended Operation Watchdogs |
| PL-6 | PL | unmapped | Third-Party Skill/Module Supply-Chain Controls |
| PL-7 | PL | unmapped | Source Reliability and Claim Handling |
| PMDESK-1 | PMDESK | unmapped | Layered Desk Runtime Separation |
| PMDESK-10 | PMDESK | unmapped | On-Chain Settlement-Aware Monitoring |
| PMDESK-11 | PMDESK | unmapped | Event-Driven Data Backbone Requirements |
| PMDESK-12 | PMDESK | unmapped | Infrastructure and Reliability Baseline |
| PMDESK-2 | PMDESK | unmapped | Bayesian Probability Update Engine |
| PMDESK-3 | PMDESK | unmapped | Cross-Market Dependency Graph Enforcement |
| PMDESK-4 | PMDESK | unmapped | Calibration Surface and Bias Diagnostics |
| PMDESK-5 | PMDESK | unmapped | Uncertainty-Adjusted Kelly Sizing |
| PMDESK-6 | PMDESK | unmapped | Microstructure-Aware Execution Algorithms |
| PMDESK-7 | PMDESK | unmapped | Informed-Flow and Liquidity Kill Switches |
| PMDESK-8 | PMDESK | unmapped | Portfolio Risk Guardrails (VaR + Drawdown) |
| PMDESK-9 | PMDESK | unmapped | Cross-Venue Price Discovery and Latency Arb Module |
| PS-1 | PS | unmapped | Low-Price Candidate Scanner |
| PS-2 | PS | unmapped | Basket Campaign Construction |
| PS-3 | PS | unmapped | Hit-Rate and Expectancy Guardrails |
| PS-4 | PS | unmapped | High-Volume Settlement and Accounting |
| PS-5 | PS | unmapped | External Wallet/Bot Signal Hygiene |
| PS-6 | PS | unmapped | Throughput, Rate-Limit, and Latency Controls |
| PS-7 | PS | unmapped | Source Reliability and Claim Handling |
| QF-1 | QF | unmapped | Composite Edge Signal |
| QF-2 | QF | unmapped | LMSR-Aware Market Modeling |
| QF-3 | QF | unmapped | Sequential Bayesian Update Loop |
| QF-4 | QF | unmapped | Explicit EV Entry Gate |
| QF-5 | QF | unmapped | Fractional Kelly Sizing Policy |
| QF-6 | QF | unmapped | Strategy Archetype Module Support |
| QF-7 | QF | unmapped | Publish-vs-Behavior Divergence Mining |
| QF-8 | QF | unmapped | Live Ops Hub and Sandbox Requirements |
| QF-9 | QF | unmapped | Source Reliability and Claim Handling |
| RBI-1 | RBI | unmapped | Research-Backtest-Incubate (RBI) Pipeline |
| RBI-2 | RBI | unmapped | Multi-Agent Role Separation |
| RBI-3 | RBI | unmapped | Parallel Experiment Orchestration |
| RBI-4 | RBI | unmapped | Promotion Gate Before Incubation |
| RBI-5 | RBI | unmapped | Feature/Filter Ablation Requirements |
| RBI-6 | RBI | unmapped | Model Routing, Cost, and Reasoning-Budget Controls |
| RBI-7 | RBI | unmapped | Evaluation Data Breadth and Reproducibility |
| RBI-8 | RBI | unmapped | Source Reliability and Claim Handling |
| RK-1 | RK | unmapped | Model Stack and Probability Calibration |
| RK-2 | RK | unmapped | Explicit Edge Threshold Gate |
| RK-3 | RK | unmapped | Risk Gate Sequence and Latency Budget |
| RK-4 | RK | unmapped | Fractional Kelly and Bankroll Caps |
| RK-5 | RK | unmapped | Hard Risk Limits |
| RK-6 | RK | unmapped | Signal-Quality and Microstructure Filters |
| RK-7 | RK | unmapped | Backtest Scoreboard and Category Breakdown |
| RK-8 | RK | unmapped | Simulated-vs-Live Performance Separation |
| RK-9 | RK | unmapped | Source Reliability and Claim Handling |
| RP-1 | RP | unmapped | Deterministic Metric-Backed Resolution Contracts |
| RP-2 | RP | unmapped | Verified-Data Oracle and Snapshot Finality |
| RP-3 | RP | unmapped | Startup/Founder Market Template Library |
| RP-4 | RP | unmapped | Entity-Centric Market Graph |
| RP-5 | RP | unmapped | Virtual-Credit Engagement Environment |
| RP-6 | RP | unmapped | Market Discovery and Coverage Controls |
| RP-7 | RP | unmapped | Public Activity Feed with Privacy-Safe Telemetry |
| RP-8 | RP | unmapped | Reputation Leaderboard Quality Controls |
| RP-9 | RP | unmapped | Source Reliability and Claim Handling |
| SECAPI-1 | SECAPI | unmapped | SEC-Compliant Request Identity Policy |
| SECAPI-10 | SECAPI | unmapped | Issuer Fundamentals Discovery Utilities |
| SECAPI-2 | SECAPI | unmapped | Master Ticker-to-CIK Registry Ingestion |
| SECAPI-3 | SECAPI | unmapped | Canonical CIK Normalization Contract |
| SECAPI-4 | SECAPI | unmapped | Company Submissions Metadata Pipeline |
| SECAPI-5 | SECAPI | unmapped | XBRL Company Facts Taxonomy Traversal |
| SECAPI-6 | SECAPI | unmapped | Concept-Level Time-Series Endpoint Support |
| SECAPI-7 | SECAPI | unmapped | Unit-Aware Metric Extraction |
| SECAPI-8 | SECAPI | unmapped | Form-Scoped Series Derivation |
| SECAPI-9 | SECAPI | unmapped | Tabular Normalization for Analytics Pipelines |
| SH-1 | SH | unmapped | Confidence-Ladder Order Slicing |
| SH-2 | SH | unmapped | Child-Order Sequence Integrity |
| SH-3 | SH | unmapped | Ultra-Short Horizon Regime Isolation |
| SH-4 | SH | unmapped | High-Volume Micro-Execution Reliability Budget |
| SH-5 | SH | unmapped | Source Reliability and Claim Handling |
| TD-1 | TD | unmapped | Time-to-Resolution Value Model |
| TD-2 | TD | unmapped | Hold-vs-Exit Policy Engine |
| TD-3 | TD | unmapped | Early-Exit Suppression Guard |
| TD-4 | TD | unmapped | Resolution-Centric Lifecycle Tracking |
| TD-5 | TD | unmapped | Policy A/B and Promotion Rules |
| TD-6 | TD | unmapped | Advisory on External Performance Claims |
| TVSRC-1 | TVSRC | unmapped | Public Indicator-Script Ingestion Contract |
| TVSRC-2 | TVSRC | unmapped | Pine-to-Python Translation Pipeline |
| TVSRC-3 | TVSRC | unmapped | Translation Equivalence Validation |
| TVSRC-4 | TVSRC | unmapped | Batch Backtest Factory for Large Candidate Sets |
| TVSRC-5 | TVSRC | unmapped | Filter-Augmented Variant Expansion and Ablation |
| TVSRC-6 | TVSRC | unmapped | Composite-Score Ranking from Results Registry |
| TVSRC-7 | TVSRC | unmapped | Short-Side Exit Logic Invariant Tests |
| TVSRC-8 | TVSRC | unmapped | Coverage Pipeline for Trending/Editor-Pick Script Sources |
| TVSRC-9 | TVSRC | unmapped | Source Reliability and Claim Handling |
| VR-1 | VR | unmapped | Variance-Drag Measurement Engine |
| VR-2 | VR | unmapped | Belief-vs-Actual Performance Reconciliation |
| VR-3 | VR | unmapped | Drawdown and Path-Dependency Diagnostics |
| VR-4 | VR | unmapped | Risk Calculator Workflow and Latency Targets |
| VR-5 | VR | unmapped | Reproducible Formula and Code Outputs |
| VR-6 | VR | unmapped | Data Quality and Metric Integrity Controls |
| VR-7 | VR | unmapped | Source Reliability and Claim Handling |
| WA-1 | WA | unmapped | Primary Backend Framework |
| WA-2 | WA | unmapped | Primary Frontend Framework |
| WA-3 | WA | unmapped | Streamlit Role Boundary |
| WA-4 | WA | unmapped | API and Streaming Contracts |
| WA-5 | WA | unmapped | Data and Session Architecture |
| WA-6 | WA | unmapped | AuthN/AuthZ and Security |
| WA-7 | WA | unmapped | Reliability and Operability |
| WA-8 | WA | unmapped | Frontend Quality and Testing |
| WA-9 | WA | unmapped | Migration and Compatibility |
| WCR-1 | WCR | unmapped | Multi-Source Search Adapter Framework |
| WCR-2 | WCR | unmapped | Recency-Normalized Aggregation |
| WCR-3 | WCR | unmapped | Canonical URL Resolution |
| WCR-4 | WCR | unmapped | Robust JS-Heavy Page Parsing Pipeline |
| WCR-5 | WCR | unmapped | Link Graph Extraction Capability |
| WCR-6 | WCR | unmapped | Resource and Session Controls for Ingestion |
| WCR-7 | WCR | unmapped | Parse Output Quality Contract |
| WCR-8 | WCR | unmapped | Real-Site Integration Test Coverage |
| WF-1 | WF | unmapped | Wallet-Flow Context Stream |
| WF-2 | WF | unmapped | Whale Quorum Trigger Logic |
| WF-3 | WF | unmapped | Pre-Move Entry and Immediate Hedge Workflow |
| WF-4 | WF | unmapped | Locked-Spread Validation |
| WF-5 | WF | unmapped | Latency and Reliability Gates for Whale-Flow Strategy |
| WF-6 | WF | unmapped | Safety and Scope Controls |
| WF-7 | WF | unmapped | External Claim Handling |
| WK-1 | WK | unmapped | Market Scope and Horizon Controls |
| WK-10 | WK | unmapped | Copytrade Endpoint Hygiene and Claim Handling |
| WK-2 | WK | unmapped | Signal Families: Probability Gap and Parity Gap |
| WK-3 | WK | unmapped | Sequential Probability Update Engine |
| WK-4 | WK | unmapped | Latency SLO and Execution Pipeline |
| WK-5 | WK | unmapped | Throughput Reliability and Order-Safety Controls |
| WK-6 | WK | unmapped | Expected Value and Sizing Discipline |
| WK-7 | WK | unmapped | Regime-Adaptive Risk Scaling |
| WK-8 | WK | unmapped | External Prediction Source Governance |
| WK-9 | WK | unmapped | Public Profile Reconciliation and Tail-Loss Visibility |
| WR-1 | WR | unmapped | Two-Sided Liquidity Provisioning Mode |
| WR-2 | WR | unmapped | Fill-State Outcome Engine |
| WR-3 | WR | unmapped | Reward-Aware Net PnL Decomposition |
| WR-4 | WR | unmapped | One-Leg Fill Hedge Controls |
| WR-5 | WR | unmapped | Niche-Market Competition Scoring |
| WR-6 | WR | unmapped | Source Reliability and Claim Handling |

