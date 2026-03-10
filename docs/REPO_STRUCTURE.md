# Repository Structure

This repository uses a "thin root" layout so contributors can find runtime code quickly.

## Root Principles

Keep files in the repository root only when they are required by tooling conventions,
packaging, or primary entrypoints.

Root should contain only:

- packaging/build metadata (`pyproject.toml`, `requirements*.txt`, `requirements.in`, `requirements.lock`)
- top-level runtime/dev entrypoints (`main.py`, `Makefile`, `docker-compose.yml`, `Dockerfile`)
- legal/provenance files (`LICENSE`, `NOTICE`, `CITATION.cff`, `CHANGELOG.md`)
- high-signal onboarding files (`README.md`, `AGENTS.md`)
- top-level config consumed by tools (`mkdocs.yml`, `.gitignore`, `.gitattributes`, `.dockerignore`)

## Directory Map

- `src/`: application/runtime code and modular-monolith boundaries
- `apps/`: executable app wrappers and launch-oriented scripts (for example `apps/demo.py`)
- `services/`: network services (for example FastAPI control-plane service)
- `scripts/`: operational tooling and workflow automation scripts
- `tools/`: architecture/quality enforcement and repository checks
- `config/`: trading/runtime configuration profiles
- `docs/`: specifications, roadmaps, runbooks, and implementation guidance
- `.github/`: collaboration and governance policy docs + CI workflows
- `tests/`: unit/integration/regression tests
- `native/`: Rust/PyO3 hot-path workspace
- `data/`: generated runtime data and reports
- `results/`: published reproducible result bundles

## Governance Docs

Community and policy docs are intentionally under `.github/`:

- `.github/CONTRIBUTING.md`
- `.github/CODE_OF_CONDUCT.md`
- `.github/SECURITY.md`
- `.github/SUPPORT.md`

This keeps the root focused on runtime and packaging concerns while preserving
GitHub-native discovery of governance materials.
