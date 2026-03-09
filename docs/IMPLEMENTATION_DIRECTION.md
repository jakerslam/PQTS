# Implementation Direction

Last updated: 2026-03-09 (America/Denver)

## North-Star Objectives

1. Fast to run
2. Maintainable
3. Easy to understand
4. Easy to add new modules
5. Easy for AI coders to traverse and modify safely

## Architecture Direction

- Primary architecture: modular monolith.
- Canonical layers:
  - `app/` composition and runtime entrypoints
  - `contracts/` typed interfaces and event/context contracts
  - `modules/` domain module lifecycle units
  - `adapters/` external I/O integrations
- Existing domain packages remain in place during migration and are composed through `app/`.

## Language Direction

- Python remains the system default for runtime, execution logic, risk gating, and orchestration.
- SQL/DuckDB/Polars-style processing should be used for large analytical scans and aggregation-heavy workloads.
- R remains supported as an optional research validator bridge for experiment gate metrics.
- Rust/C++ is deferred unless profiling proves hard latency limits cannot be met with Python + optimized data paths.

## R Integration Position

- Implemented and available:
  - `research/r_analytics_bridge.py`
  - `scripts/r/validate_experiment.R`
- Intended role:
  - optional validation layer for research promotion gates
  - not a required dependency for core trading runtime
- Default posture:
  - enabled selectively where research rigor benefits from R-side stats workflows

## Delivery Rules

- Incremental migration only; no destabilizing rewrites.
- Preserve CLI/script compatibility while moving logic into canonical layers.
- Every structural change should include:
  - boundary validation (`tools/check_architecture_boundaries.py`)
  - architecture map check (`tools/print_architecture_map.py`)
  - focused tests for new contracts/tooling.

## Compliance References

- `docs/CODEX_COMPLIANCE.md`
- `docs/ARCHITECTURE.md`
