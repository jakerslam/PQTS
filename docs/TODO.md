# PQTS Engineering TODO

Last updated: 2026-03-09 (America/Denver)

Execution rule: complete phases top-to-bottom. Do not start a later phase until all blocking items in earlier phases are done.

Issue-ready split backlog: [docs/ISSUE_BACKLOG.md](/Users/jay/Document%20(Lcl)/Coding/PQTS/docs/ISSUE_BACKLOG.md)

## 00. Foundation Done

- [x] Add `LICENSE` file with MIT text.
- [x] Add GitHub Actions CI coverage for `pytest`, `ruff`, `mypy`, architecture checks, and security scan.
- [x] Add README badges for CI and package/release status.
- [x] Add Docker + `docker-compose` one-command runtime stack.
- [x] Add automated simulation leaderboard static export + GitHub Pages publish workflow.
- [x] Add benchmark/results documentation templates for reproducible publication.
- [x] Finalize PyPI publication workflow (`pip install pqts`) and release credential docs.
- [x] Add release checklist docs and branch protection guidance.

## 01. Core Runtime Contracts + API Platform (`P0`)

- [x] Create canonical schemas for account, positions, orders, fills, PnL snapshots, risk state, tool payloads, and error envelopes.
- [x] Create `services/api` FastAPI service scaffold with health/readiness endpoints and OpenAPI generation.
- [x] Implement API auth foundation (session/token flow + role model) and protect privileged endpoints.
- [x] Implement core REST endpoints: account summary, positions, orders, fills, PnL snapshots, risk state.
- [x] Implement core WebSocket channels: orders, fills, positions, PnL, risk/kill-switch incidents.
- [x] Add Postgres-backed persistence layer + migration scripts for API/web entities.
- [x] Add Redis-backed cache/session/rate-limit layer for API and stream control.
- [x] Add trace/run correlation IDs across API, tools, streams, and UI events.

## 02. Market + SEC Data Fabric (`P0`)

- [x] Implement SEC-compliant request identity config (`User-Agent`) with runtime validation.
- [x] Build master ticker→CIK ingestion pipeline from SEC `company_tickers.json`.
- [x] Add canonical CIK normalization utility (int and zero-padded 10-digit string forms).
- [x] Implement SEC submissions ingestion (`CIK{cik}.json`) with form/date/accession normalization.
- [x] Implement SEC `companyfacts` taxonomy traversal (`dei`, `us-gaap`) with missing-tag-safe parsing.
- [x] Implement SEC `companyconcept` metric endpoint adapter with taxonomy/concept validation.
- [x] Add unit-aware metric extraction (`USD`, `shares`, etc.) and form-scoped filters (10-Q/10-K).
- [x] Add tabular normalization layer for SEC payloads with accession/report-date traceability.
- [x] Implement multi-source retrieval surface (structured market/financial + web/news) with provenance metadata.
- [x] Add provider adapter error envelopes and response-shape normalization for all external connectors.

## 03. Execution + Risk Intelligence (`P1`)

- [x] Implement Bayesian probability update engine with persisted prior/evidence/posterior metadata.
- [x] Implement cross-market dependency graph + logical constraint checks + violation alerts.
- [x] Build calibration surface pipeline and mispricing diagnostics (bucket/regime based).
- [x] Implement uncertainty-adjusted Kelly sizing with caps and minimum-edge gates.
- [x] Implement VWAP/TWAP/depth-aware execution slicing and execution quality telemetry.
- [x] Add orderbook sequence-gap detection and deterministic resync/recovery logic.
- [x] Implement informed-flow/liquidity indicators (including VPIN-style) and automated quote/size kill switches.
- [x] Add portfolio VaR + drawdown guardrails with automatic new-risk gating.
- [x] Implement cross-venue dislocation detection and hedged routing planner.
- [x] Add on-chain settlement state monitoring and resolution-window risk controls.

## 04. Web App + Generative UI (`P1`)

- [x] Create `apps/web` Next.js + TypeScript app scaffold with API client/env wiring.
- [x] Build authenticated dashboard shell (navigation, auth-aware routing, error boundaries).
- [x] Implement first production pages: portfolio overview, orders/fills tape, risk/alerts panel.
- [x] Add tool-aware UI registry mapping tool type → loading component + final component + fallback renderer.
- [x] Implement stream-event orchestrator for LLM token stream + tool lifecycle events.
- [x] Implement optimistic user-turn rendering with rollback/error reconciliation.
- [x] Add input UX controls (Enter submit, Shift+Enter newline, duplicate-submit prevention).
- [x] Add scroll anchoring + “scroll to latest” behavior for streaming sessions.
- [x] Add rich markdown/table/code rendering with safe outbound-link defaults.
- [x] Add operator action workflows (pause/resume mechanisms, canary decisions, incident acknowledgment).
- [x] Add frontend/unit integration tests for critical components and data hooks.
- [x] Add end-to-end smoke tests for login, dashboard load, stream subscribe, and risk-state rendering.

## 05. Research Dataset + Evaluation Pipeline (`P1`)

- [x] Implement multi-source corpus ingestion (text list, PDF URL, 10-K, 10-Q) with unified normalization.
- [x] Add deterministic text cleanup and token-aware chunking (size + overlap) with provenance.
- [x] Implement question budget allocator (per-chunk allocation + global cap enforcement).
- [x] Implement strict function-call schema output (`question`, `answer`, `context`) with schema validation.
- [x] Enforce grounded standalone QA quality policy and reject source-referential leakage phrasing.
- [x] Add provider guardrails + bounded retry/backoff for generation calls.
- [x] Implement two-stage retrieval→reasoning pipeline with stable evidence IDs (`text_i`, `table_j`).
- [x] Add top-k retrieval recall reporting and full-ranked-list persistence for audits.
- [x] Implement executable program DSL scoring with dual metrics: execution accuracy + symbolic program equivalence.
- [x] Implement blind/private-test evaluation mode and strict submission schema validation.
- [x] Add leakage regression tests for preprocessing functions and prompt-output schema integrity.

## 06. Reliability, Security, and Operability (`P2`)

- [x] Add API/web SLO instrumentation and dashboards (latency, error rate, availability).
- [x] Add health endpoints and deployment profiles with explicit concurrency and graceful shutdown controls.
- [x] Add event-stream backbone hardening (durable events, replay support for incident forensics).
- [x] Add secrets management policy (rotation cadence, environment gating, non-exposure checks).
- [ ] Add release gating with build provenance artifact upload/verification.
- [ ] Add frontend/backend contract tests for graph node events and tool renderer mapping completeness.
- [ ] Add migration parity checks between Streamlit and Next.js outputs for key metrics.
- [ ] Document Streamlit deprecation milestones once parity is green.

## 07. Benchmarking and Publication (`P2`)

- [ ] Capture first published benchmark baselines in [docs/BENCHMARKS.md](/Users/jay/Document%20(Lcl)/Coding/PQTS/docs/BENCHMARKS.md) from reproducible runs.
- [ ] Publish at least three reproducible result bundles under `results/` with configs, metrics, and charts.
- [ ] Add monthly automated report generation (HTML/PDF + equity curve + Sharpe/DD + attribution tables).
- [ ] Add benchmark provenance log (strategy version, dataset/version, environment hash, run timestamp).
