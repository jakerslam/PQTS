# PQTS Issue Backlog

Last updated: 2026-03-12 (America/Denver)

This file splits every open item in `docs/TODO.md` into issue-ready tickets with stable IDs and explicit dependencies.

Status note:
- Treat this document as a historical issue template archive.
- Canonical active execution order is maintained in `docs/TODO.md`.
- Canonical requirement source of truth is `docs/SRS.md`.
- Any item already implemented in code/tests should be considered closed even if still listed here.

## How To Use

0. Optional automation script:
   - Dry-run: `bash scripts/create_github_issues_from_backlog.sh --dry-run`
   - Create all: `bash scripts/create_github_issues_from_backlog.sh --execute`
1. Create GitHub issues in ID order within each phase.
2. Use title prefix exactly as shown (`[Feature]:` / `[Docs]:`).
3. Apply labels exactly as listed.
4. Copy `Scope` into "Proposed Solution" and use the default acceptance criteria plus any ticket-specific notes.

## Default Acceptance Criteria

For all `[Feature]` tickets unless overridden:

- Behavior is implemented end-to-end and wired into existing runtime paths.
- Tests are added/updated for changed behavior (unit/integration; e2e where relevant).
- Telemetry/error handling and docs are updated for new/changed contracts.

For all `[Docs]` tickets unless overridden:

- Referenced files are updated with accurate, current behavior.
- Docs include links to concrete code paths/commands.
- Docs changes are validated for consistency with `docs/TODO.md` and `docs/SRS.md`.

## Phase 01 - Core Runtime Contracts + API Platform (`P0`)

### PQTS-001 `[Feature]: Create canonical domain schemas for API/web/runtime`
- Labels: `enhancement`, `priority/p0`
- Depends on: `none`
- Scope: Define canonical models for account, positions, orders, fills, PnL snapshots, risk state, tool payloads, and error envelopes.

### PQTS-002 `[Feature]: Scaffold services/api FastAPI platform with health/openapi`
- Labels: `enhancement`, `priority/p0`
- Depends on: `PQTS-001`
- Scope: Create `services/api` FastAPI scaffold with readiness/liveness endpoints and OpenAPI generation.

### PQTS-003 `[Feature]: Implement API auth foundation and role guards`
- Labels: `enhancement`, `priority/p0`
- Depends on: `PQTS-002`
- Scope: Add token/session auth, role model, and privileged endpoint protections.

### PQTS-004 `[Feature]: Implement core REST endpoints for account/portfolio/execution/risk`
- Labels: `enhancement`, `priority/p0`
- Depends on: `PQTS-001`, `PQTS-002`, `PQTS-003`
- Scope: Add REST endpoints for account summary, positions, orders, fills, PnL snapshots, and risk state.

### PQTS-005 `[Feature]: Implement core realtime WebSocket channels`
- Labels: `enhancement`, `priority/p0`
- Depends on: `PQTS-001`, `PQTS-002`, `PQTS-003`
- Scope: Add WS channels for orders, fills, positions, PnL, and risk/kill-switch incidents.

### PQTS-006 `[Feature]: Add Postgres persistence and migration baseline`
- Labels: `enhancement`, `priority/p0`
- Depends on: `PQTS-001`, `PQTS-002`
- Scope: Introduce Postgres-backed persistence for API/web entities with migration scripts.

### PQTS-007 `[Feature]: Add Redis cache/session/rate-limit layer`
- Labels: `enhancement`, `priority/p0`
- Depends on: `PQTS-001`, `PQTS-002`
- Scope: Add Redis for cache/session/rate-limiting and stream-control primitives.

### PQTS-008 `[Feature]: Add trace and run correlation IDs across stack`
- Labels: `enhancement`, `priority/p0`
- Depends on: `PQTS-002`
- Scope: Propagate run/trace IDs across API, tools, stream events, and UI handlers.

## Phase 02 - Market + SEC Data Fabric (`P0`)

### PQTS-009 `[Feature]: Enforce SEC-compliant requester identity configuration`
- Labels: `enhancement`, `priority/p0`
- Depends on: `PQTS-002`
- Scope: Add required SEC `User-Agent` identity config and runtime validation.

### PQTS-010 `[Feature]: Build ticker-to-CIK master ingestion pipeline`
- Labels: `enhancement`, `priority/p0`
- Depends on: `PQTS-009`
- Scope: Ingest and normalize SEC `company_tickers.json` into canonical issuer mapping.

### PQTS-011 `[Feature]: Implement canonical CIK normalization utility`
- Labels: `enhancement`, `priority/p0`
- Depends on: `PQTS-010`
- Scope: Support both raw integer and zero-padded 10-digit CIK forms in one utility.

### PQTS-012 `[Feature]: Implement SEC submissions metadata ingestion adapter`
- Labels: `enhancement`, `priority/p0`
- Depends on: `PQTS-011`
- Scope: Build `CIK{cik}.json` ingestion with accession/form/report-date normalization.

### PQTS-013 `[Feature]: Implement SEC companyfacts taxonomy traversal`
- Labels: `enhancement`, `priority/p0`
- Depends on: `PQTS-011`
- Scope: Parse `companyfacts` across `dei`/`us-gaap` with missing-tag-safe behavior.

### PQTS-014 `[Feature]: Implement SEC companyconcept metric adapter`
- Labels: `enhancement`, `priority/p0`
- Depends on: `PQTS-011`
- Scope: Build concept endpoint client with taxonomy/concept validation and error handling.

### PQTS-015 `[Feature]: Add unit-aware extraction and form-scoped filters`
- Labels: `enhancement`, `priority/p0`
- Depends on: `PQTS-013`, `PQTS-014`
- Scope: Add unit selection (`USD`, `shares`, etc.) plus 10-Q/10-K scoped extraction.

### PQTS-016 `[Feature]: Add tabular normalization for SEC analytics payloads`
- Labels: `enhancement`, `priority/p0`
- Depends on: `PQTS-013`, `PQTS-014`
- Scope: Normalize SEC JSON to stable tabular schemas with accession/report-date traceability.

### PQTS-017 `[Feature]: Implement multi-source retrieval surface with provenance`
- Labels: `enhancement`, `priority/p0`
- Depends on: `PQTS-016`
- Scope: Combine structured financial/market + web/news retrieval with source provenance metadata.

### PQTS-018 `[Feature]: Standardize provider adapter error envelopes and shapes`
- Labels: `enhancement`, `priority/p0`
- Depends on: `PQTS-013`, `PQTS-014`, `PQTS-017`
- Scope: Enforce consistent adapter response and error contracts across external connectors.

## Phase 03 - Execution + Risk Intelligence (`P1`)

### PQTS-019 `[Feature]: Implement Bayesian probability update engine`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-004`, `PQTS-005`, `PQTS-017`
- Scope: Build posterior update engine with persisted prior/evidence/posterior metadata.

### PQTS-020 `[Feature]: Implement cross-market dependency graph checks`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-019`
- Scope: Add logical constraint enforcement and violation alerts for related markets.

### PQTS-021 `[Feature]: Build calibration surface and mispricing diagnostics pipeline`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-019`
- Scope: Generate bucket/regime calibration reports and actionable mispricing diagnostics.

### PQTS-022 `[Feature]: Implement uncertainty-adjusted Kelly sizing policy`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-019`, `PQTS-021`
- Scope: Add capped fractional Kelly sizing with uncertainty penalties and edge thresholds.

### PQTS-023 `[Feature]: Implement execution slicing algorithms and quality telemetry`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-004`, `PQTS-005`, `PQTS-022`
- Scope: Add VWAP/TWAP/depth-aware slicing plus slippage/time-to-fill telemetry.

### PQTS-024 `[Feature]: Add orderbook sequence-gap detection and deterministic recovery`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-023`
- Scope: Detect feed sequence gaps and resync local orderbook state safely.

### PQTS-025 `[Feature]: Implement informed-flow indicators and quote kill-switch logic`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-023`, `PQTS-024`
- Scope: Compute VPIN-style/liquidity stress signals and automate protective execution actions.

### PQTS-026 `[Feature]: Implement VaR and drawdown risk guardrails`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-022`, `PQTS-025`
- Scope: Add rolling VaR/drawdown checks with automatic new-risk gating.

### PQTS-027 `[Feature]: Implement cross-venue dislocation detection and hedged routing`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-017`, `PQTS-025`
- Scope: Detect cross-venue temporary dislocations and construct hedged execution plans.

### PQTS-028 `[Feature]: Add on-chain settlement state monitoring and controls`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-026`, `PQTS-027`
- Scope: Monitor settlement/resolution transitions and tighten risk controls near resolution windows.

## Phase 04 - Web App + Generative UI (`P1`)

### PQTS-029 `[Feature]: Scaffold apps/web Next.js TypeScript frontend`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-002`, `PQTS-004`, `PQTS-005`
- Scope: Create web app skeleton with API client and environment wiring.

### PQTS-030 `[Feature]: Implement authenticated dashboard shell and route guards`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-029`, `PQTS-003`
- Scope: Build auth-aware shell, navigation, and error boundary scaffolding.

### PQTS-031 `[Feature]: Build first production web pages for portfolio/execution/risk`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-030`, `PQTS-004`, `PQTS-005`
- Scope: Implement portfolio overview, orders/fills tape, and risk/alerts panels.

### PQTS-032 `[Feature]: Implement tool-aware UI renderer registry with fallback`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-031`
- Scope: Map tool types to loading/final widgets with safe unknown-tool fallback.

### PQTS-033 `[Feature]: Implement LLM/tool stream-event orchestrator for UI`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-032`
- Scope: Handle token streams and tool lifecycle events in a single assistant turn.

### PQTS-034 `[Feature]: Implement optimistic user-turn rendering with reconciliation`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-033`
- Scope: Add optimistic message append and robust rollback/error reconcile behavior.

### PQTS-035 `[Feature]: Add chat input UX controls for high-velocity operation`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-029`
- Scope: Add Enter submit, Shift+Enter newline, trim/duplicate-send prevention.

### PQTS-036 `[Feature]: Add scroll anchoring and scroll-to-latest behavior`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-029`
- Scope: Implement bottom tracking and non-disruptive auto-scroll for streaming chats.

### PQTS-037 `[Feature]: Implement rich markdown/table/code assistant rendering`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-029`
- Scope: Add markdown rendering with safe outbound link defaults and table/code support.

### PQTS-038 `[Feature]: Implement operator action workflows in web app`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-031`, `PQTS-033`
- Scope: Add pause/resume, canary decisions, and incident acknowledgment flows.

### PQTS-039 `[Feature]: Add frontend unit/integration test suite for critical paths`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-031`, `PQTS-032`
- Scope: Cover core components, hooks, and tool-rendering contracts.

### PQTS-040 `[Feature]: Add e2e smoke tests for auth/dashboard/stream/risk rendering`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-031`, `PQTS-032`, `PQTS-033`
- Scope: Add user-journey smoke tests for login, load, subscription, and risk-state updates.

## Phase 05 - Research Dataset + Evaluation Pipeline (`P1`)

### PQTS-041 `[Feature]: Implement multi-source corpus ingestion for evaluation datasets`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-018`
- Scope: Support text/PDF/10-K/10-Q ingestion with unified normalization.

### PQTS-042 `[Feature]: Add deterministic cleanup and token-aware chunking layer`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-041`
- Scope: Build deterministic cleanup and configurable chunk-size/overlap preprocessing.

### PQTS-043 `[Feature]: Implement global question budget allocation policy`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-042`
- Scope: Allocate per-chunk budgets with deterministic remainder handling and global cap.

### PQTS-044 `[Feature]: Enforce strict function-call output schema for dataset items`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-041`, `PQTS-043`
- Scope: Require schema-valid `question`/`answer`/`context` outputs from generation calls.

### PQTS-045 `[Feature]: Implement grounded standalone QA quality policy checks`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-044`
- Scope: Reject source-referential leakage phrasing and enforce grounded standalone answers.

### PQTS-046 `[Feature]: Implement provider guardrails with bounded retry/backoff`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-044`
- Scope: Add provider constraints and retry policy for resilient generation workflows.

### PQTS-047 `[Feature]: Implement two-stage retrieval-to-reasoning pipeline`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-041`
- Scope: Build retriever+reasoner flow with stable evidence IDs (`text_i`, `table_j`).

### PQTS-048 `[Feature]: Add top-k retrieval recall and full-rank artifact persistence`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-047`
- Scope: Compute top-k recall and persist full ranked evidence lists for diagnostics.

### PQTS-049 `[Feature]: Implement executable program DSL dual-metric scoring`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-047`, `PQTS-048`
- Scope: Add execution-accuracy plus symbolic program-equivalence scoring.

### PQTS-050 `[Feature]: Implement private/blind evaluation mode and submission validation`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-049`
- Scope: Support blind split execution mode with strict submission format validation.

### PQTS-051 `[Feature]: Add leakage regression suite for preprocessing and outputs`
- Labels: `enhancement`, `priority/p1`
- Depends on: `PQTS-041`, `PQTS-042`, `PQTS-044`
- Scope: Add regression tests covering leakage, schema drift, and preprocessing consistency.

## Phase 06 - Reliability, Security, Operability (`P2`)

### PQTS-052 `[Feature]: Add API/web SLO instrumentation and operational dashboards`
- Labels: `enhancement`, `priority/p2`
- Depends on: `PQTS-004`, `PQTS-005`, `PQTS-029`
- Scope: Instrument latency/error/availability metrics and publish operator dashboards.

### PQTS-053 `[Feature]: Harden health/readiness and deployment profile controls`
- Labels: `enhancement`, `priority/p2`
- Depends on: `PQTS-002`
- Scope: Add explicit health checks, concurrency limits, and graceful shutdown settings.

### PQTS-054 `[Feature]: Harden event-stream backbone with replay support`
- Labels: `enhancement`, `priority/p2`
- Depends on: `PQTS-005`, `PQTS-052`
- Scope: Add durable stream semantics and replay paths for incident forensics.

### PQTS-055 `[Feature]: Implement secrets management policy and enforcement checks`
- Labels: `enhancement`, `priority/p2`
- Depends on: `PQTS-053`
- Scope: Define rotation cadence, env gating, and non-exposure checks for sensitive keys.

### PQTS-056 `[Feature]: Add release gating with provenance artifact verification`
- Labels: `enhancement`, `priority/p2`
- Depends on: `PQTS-052`, `PQTS-054`
- Scope: Enforce release gates requiring provenance artifacts and verification checks.

### PQTS-057 `[Feature]: Add frontend/backend contract tests for stream and tool mapping`
- Labels: `enhancement`, `priority/p2`
- Depends on: `PQTS-032`, `PQTS-033`
- Scope: Verify graph event contracts and tool renderer mapping completeness.

### PQTS-058 `[Feature]: Add Streamlit-to-web parity checks for key metrics`
- Labels: `enhancement`, `priority/p2`
- Depends on: `PQTS-031`
- Scope: Build parity harness comparing key metrics between Streamlit and Next.js surfaces.

### PQTS-059 `[Docs]: Document Streamlit deprecation milestones and cutoff plan`
- Labels: `documentation`, `priority/p2`
- Depends on: `PQTS-058`
- Scope: Document migration milestones, parity criteria, and deprecation execution timeline.

## Phase 07 - Benchmarking + Publication (`P2`)

### PQTS-060 `[Docs]: Publish first reproducible benchmark baselines`
- Labels: `documentation`, `priority/p2`
- Depends on: `PQTS-058`
- Scope: Populate `docs/BENCHMARKS.md` with first reproducible baseline results.

### PQTS-061 `[Feature]: Publish three reproducible results bundles under results/`
- Labels: `enhancement`, `priority/p2`
- Depends on: `PQTS-060`
- Scope: Commit at least three reproducible result bundles with config, metrics, and charts.

### PQTS-062 `[Feature]: Add monthly automated report generation pipeline`
- Labels: `enhancement`, `priority/p2`
- Depends on: `PQTS-060`, `PQTS-061`
- Scope: Generate monthly HTML/PDF reports with equity curve, Sharpe/DD, and attribution tables.

### PQTS-063 `[Feature]: Implement benchmark provenance logging standard`
- Labels: `enhancement`, `priority/p2`
- Depends on: `PQTS-060`, `PQTS-061`, `PQTS-062`
- Scope: Record strategy version, dataset/version, environment hash, and run timestamps for published benchmarks.
