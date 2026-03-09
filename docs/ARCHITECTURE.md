# PQTS Architecture

## Goals

- Fast runtime execution (single-process modular monolith).
- Maintainable boundaries (strict layer contracts).
- Easy to understand and traverse.
- Easy to add modules.
- AI-friendly structure with deterministic entrypoints.

## Canonical References

- `docs/CODEX_COMPLIANCE.md`
- `docs/IMPLEMENTATION_DIRECTION.md`
- `docs/ARCHITECTURE.md` (this document)

## Canonical Layout

- `app/`: composition root, CLI wiring, runtime startup.
- `contracts/`: shared typed contracts (`RuntimeContext`, module descriptors, event envelopes).
- `modules/`: business modules with explicit dependencies and lifecycle hooks.
- `adapters/`: external I/O adapter descriptors and loading helpers.

Legacy domain code remains in place during migration:
- `core/`, `execution/`, `analytics/`, `risk/`, `strategies/`, `markets/`, etc.

## Language Strategy

- Python is the default language for runtime execution, risk controls, orchestration, and strategy logic.
- SQL/DuckDB/Polars-style data processing is preferred for heavy analytical aggregation workloads.
- R is supported as an optional research validator path and is not required for core runtime operation.
- Rust/C++ adoption is gated by measured latency/SLO evidence from profiling.

## Dependency Rules

Canonical layer rules enforced by `tools/check_architecture_boundaries.py`:

- `contracts` may import only `contracts`.
- `adapters` may import only `adapters` and `contracts`.
- `modules` may import only `modules`, `adapters`, and `contracts`.
- `app` may import any canonical layer.

## Runtime Composition

- Entry: `main.py` -> `app.runtime.main`.
- Bootstrap: `app.bootstrap.bootstrap_runtime`.
- Registry: `app.module_registry.ModuleRegistry`.
- Built-in modules (ordered by dependencies):
  - `data`
  - `signals`
  - `risk`
  - `strategies`
  - `execution`
  - `analytics`

## R Analytics Boundary

- Optional bridge:
  - `research/r_analytics_bridge.py`
  - `scripts/r/validate_experiment.R`
- R validation may gate research promotion when explicitly enabled.
- Core runtime and execution paths must remain operational without R.

## Developer Commands

- Boundary check: `python tools/check_architecture_boundaries.py`
- Architecture map: `python tools/print_architecture_map.py`
- Module scaffold: `python tools/scaffold_module.py <name> --requires data,signals --provides my_capability`

## Adding a New Module

1. Add a module class in `modules/<name>.py` with a `ModuleDescriptor`.
2. Declare `requires` dependencies explicitly.
3. Register it in `modules.get_default_modules()`.
4. Run boundary and tests.
