# Implementation Direction

Last updated: 2026-03-17 (America/Denver)

## Product Framing

- Tagline: `PQTS monetizes future predictions under explicit EV, risk, provenance, and promotion gates.`
- Scope sentence: `Prediction markets are the primary trading surface; adjacent tradable forecasting venues use the same control plane when they satisfy the same safety and eligibility contracts.`
- Product wedge: prediction-market-first and forecast-monetization-first, not generic brokerage breadth for its own sake.

## North-Star Objectives

1. Make monetizing future predictions trustworthy and repeatable
2. Fast to run
3. Maintainable
4. Easy to understand
5. Easy to add new modules
6. Easy for AI coders to traverse and modify safely

## Architecture Direction

- Primary architecture: modular monolith.
- Primary product posture: governed forecast-to-capital decisions on prediction markets first.
- Canonical layers:
  - `src/app/` composition and runtime entrypoints
  - `src/contracts/` typed interfaces and event/context contracts
  - `src/modules/` domain module lifecycle units
  - `src/adapters/` external I/O integrations
- Existing domain packages remain in place during migration and are composed through `src/app/`.

## Language Direction

- Python remains the system default for runtime, execution logic, risk gating, and orchestration.
- The product target is Python-first (not Python-only): user-facing surface remains mostly Python, while hot-path kernels migrate to Rust when profiling triggers are met.
- FastAPI is the canonical control plane; all active surfaces consume API contracts.
- Next.js (`apps/web`) is the primary external Studio surface.
- Dash (`src/dashboard/start.py`) remains operator/internal fallback during cutover windows.
- DuckDB/Polars/PyArrow remain the preferred analytical data-plane stack for heavy scan/aggregation paths.
- R remains supported as an optional research validator bridge for experiment gate metrics.

## R Integration Position

- Implemented and available:
  - `src/research/r_analytics_bridge.py`
  - `scripts/r/validate_experiment.R`
- Intended role:
  - optional validation layer for research promotion gates
  - not a required dependency for core trading runtime
- Default posture:
  - enabled selectively where research rigor benefits from R-side stats workflows

## Delivery Rules

- Incremental migration only; no destabilizing rewrites.
- Preserve CLI/script compatibility while moving logic into canonical layers.
- Prefer prediction-market and forecast-monetization implementations when choosing between equally valuable expansion paths.
- Keep one primary runtime path per release phase (no mixed Streamlit/Dash runtime ambiguity), and maintain all public proof/docs claims from canonical artifact feeds (`results/reference_performance_latest.json`, release-readiness outputs, and `docs/REFERENCE_PERFORMANCE.md`).
- Enforce typed boundaries (Pydantic models) for runtime config, API payloads, and strategy manifests.
- Keep manual, agent-assisted, and autopilot execution behind the shared
  trading-control mode and `OrderIntent` lifecycle documented in
  `docs/TRADING_CONTROL_PLANE.md`; do not add any UI/API shortcut around the
  router-owned execution path.
- Every structural change should include:
  - boundary validation (`tools/check_architecture_boundaries.py`)
  - architecture map check (`tools/print_architecture_map.py`)
  - stack-direction validation (`tools/check_stack_direction.py`)
  - focused tests for new contracts/tooling.

## Compliance References

- `docs/CODEX_COMPLIANCE.md`
- `docs/ARCHITECTURE.md`
