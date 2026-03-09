# PQTS Engineering TODO

Last updated: 2026-03-09 (America/Denver)

This file tracks engineering chores/fix items (not net-new product capabilities and not human-only outreach work).

## Web App SRS Implementation (Ordered by Importance)

- [ ] `P0` Create `services/api` FastAPI service scaffold with health/readiness endpoints and OpenAPI generation.
- [ ] `P0` Implement API auth foundation (session/token flow + role model) and protect privileged endpoints.
- [ ] `P0` Implement core REST endpoints: account summary, positions, orders, fills, PnL snapshots, risk state.
- [ ] `P0` Implement core WebSocket channels: orders, fills, positions, PnL, risk/kill-switch incidents.
- [ ] `P0` Add Postgres-backed persistence layer for web app entities and migration scripts.
- [ ] `P0` Add Redis-backed cache/session/rate-limit layer for API and stream control.
- [ ] `P1` Create `apps/web` Next.js + TypeScript app scaffold with API client layer and env wiring.
- [ ] `P1` Build authenticated dashboard shell (navigation, auth-aware routing, error boundaries).
- [ ] `P1` Implement first production pages in Next.js: portfolio overview, orders/fills tape, risk/alerts panel.
- [ ] `P1` Add parity checks between Streamlit and Next.js for key metrics during migration.
- [ ] `P1` Add end-to-end smoke tests for login, dashboard load, stream subscribe, and risk-state rendering.
- [ ] `P1` Add frontend unit/integration tests for critical components and data hooks.
- [ ] `P1` Add API latency/error SLO instrumentation and dashboards for web-specific services.
- [ ] `P2` Add operator action workflows in web app (pause/resume mechanisms, canary decisions, incident ack).
- [ ] `P2` Add release gating for web app builds with provenance artifact upload.
- [ ] `P2` Document migration milestones and deprecation plan for replaced Streamlit surfaces.

## P0

- [x] Add `LICENSE` file with MIT text and ensure repository metadata reflects license choice.
- [x] Add GitHub Actions CI pipeline coverage for `pytest`, `ruff`, `mypy`, architecture boundary validation, and security scan.
- [x] Add README badges for CI status and package/release status.
- [x] Add Docker + docker-compose one-command runtime stack.
- [x] Add automated simulation leaderboard static export and GitHub Pages publishing workflow.
- [x] Add benchmark/results documentation templates for reproducible publication.
- [x] Finalize PyPI publication workflow (`pip install pqts`) including trusted publishing setup and release credentials documentation.

## P1

- [x] Add release checklist doc for version bump, changelog, package build, smoke install, and publish.
- [x] Add CI branch protection guidance and required-check policy in docs.
- [ ] Capture first published benchmark baselines in `docs/BENCHMARKS.md` from reproducible runs.
