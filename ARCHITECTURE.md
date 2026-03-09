# PQTS Architecture

## Goals

- Fast runtime execution (single-process modular monolith).
- Maintainable boundaries (strict layer contracts).
- Easy to understand and traverse.
- Easy to add modules.
- AI-friendly structure with deterministic entrypoints.

## Canonical Layout

- `app/`: composition root, CLI wiring, runtime startup.
- `contracts/`: shared typed contracts (`RuntimeContext`, module descriptors, event envelopes).
- `modules/`: business modules with explicit dependencies and lifecycle hooks.
- `adapters/`: external I/O adapter descriptors and loading helpers.

Legacy domain code remains in place during migration:
- `core/`, `execution/`, `analytics/`, `risk/`, `strategies/`, `markets/`, etc.

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

## Developer Commands

- Boundary check: `python tools/check_architecture_boundaries.py`
- Architecture map: `python tools/print_architecture_map.py`
- Module scaffold: `python tools/scaffold_module.py <name> --requires data,signals --provides my_capability`

## Adding a New Module

1. Add a module class in `modules/<name>.py` with a `ModuleDescriptor`.
2. Declare `requires` dependencies explicitly.
3. Register it in `modules.get_default_modules()`.
4. Run boundary and tests.
