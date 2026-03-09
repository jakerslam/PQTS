# Codex Compliance Guide

## Purpose

This file defines the minimum compliance checklist for any coding session in PQTS.

## Required References

Before making code changes, review in this order:

1. `AGENTS.md` (root-level operating instructions)
2. `docs/CODEX_COMPLIANCE.md` (this file)
3. `docs/ARCHITECTURE.md` (canonical system structure and boundaries)
4. `docs/IMPLEMENTATION_DIRECTION.md` (current strategic implementation direction)

## Architecture Compliance

- Keep the canonical modular-monolith layout intact:
  - `app/`
  - `contracts/`
  - `modules/`
  - `adapters/`
- Enforce layer boundaries with:
  - `python tools/check_architecture_boundaries.py`
- Keep `main.py` as a compatibility entrypoint delegating to `app.runtime`.

## Language Compliance

- Use Python as the default implementation language for runtime, orchestration, and strategy logic.
- Use SQL/DuckDB/Polars-style data operations for heavy analytics where performance needs it.
- Keep R limited to optional research validation gates (`research/r_analytics_bridge.py` + `scripts/r/validate_experiment.R`).
- Do not make R a hard dependency for core trading runtime paths.
- Only introduce Rust/C++ after profiling proves Python hot paths cannot meet latency/SLO targets.

## Documentation Compliance

When architecture or language choices change, update at minimum:

1. `docs/ARCHITECTURE.md`
2. `docs/IMPLEMENTATION_DIRECTION.md`
3. Relevant subsystem doc(s), e.g. `docs/RESEARCH_ANALYTICS_LAYER.md`
4. `README.md` links if paths or primary docs changed

## Change Safety

- Prefer incremental migrations over big-bang rewrites.
- Preserve backward compatibility for existing scripts/tests unless explicitly approved.
- Add tests for new framework/tooling behavior (registry, boundaries, scaffolding).
