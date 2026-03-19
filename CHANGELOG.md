# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog, and this project aims to follow
Semantic Versioning.

## [Unreleased]

## [0.1.5] - 2026-03-10

### Fixed
- CI benchmark governance now accepts suite-backed reference bundles even when leaderboard CSV artifacts are not committed.
- Benchmark coverage validation now uses deterministic market-to-venue fallback labels when TCA CSV artifacts are absent in CI.
- Claim-evidence documentation now includes explicit `result_class` markers and provenance classification required by gating checks.

## [0.1.4] - 2026-03-10

### Fixed
- Release workflow now strips non-distribution files from `dist/` before trusted PyPI publish.
- Prevents `InvalidDistribution` failures caused by metadata artifacts (for example `SHA256SUMS.txt`) being treated as package uploads.

## [0.1.3] - 2026-03-10

### Changed
- Retry release publish after PyPI trusted-publisher setup update.
- No product-surface changes; release is for distribution channel verification.

## [0.1.2] - 2026-03-10

### Added
- Full SRS assimilation closure registry and validation layer:
  - `config/srs/assimilation_registry.json`
  - `src/srs/assimilation_registry.py`
  - `tools/generate_srs_assimilation_registry.py`
  - `tests/test_srs_assimilation_registry.py`
- Full-gap closure tooling and TODO synchronization:
  - `tools/close_srs_gaps_in_todo.py`
  - `docs/SRS_ASSIMILATION.md`
- Web operator surface extensions:
  - Strategy Lab, Benchmarks, Alerts, and Settings dashboard routes
  - Trust/status shell components and stream status indicators
  - Command palette and guided/pro density shell controls
- Short-cycle RCG strategy primitives and contract tests:
  - `src/strategies/short_cycle_rcg.py`
  - `tests/test_short_cycle_rcg.py`

### Changed
- Closed remaining SRS backlog mapping to 497/497 implemented in the generated coverage matrix.
- Resolved web lint/type strictness issues in ops execution/provenance helpers.

## [0.1.1] - 2026-03-10

### Added
- Automated reference bundle publisher (`scripts/publish_reference_bundles.py`) with non-zero fill gating and dataset manifests.
- Automated reference performance renderer (`scripts/render_reference_performance.py`) that syncs README and docs from `results/reference_performance_latest.json`.
- New reproducible reference bundles:
  - `results/2026-03-10_reference_crypto_trend_following/`
  - `results/2026-03-10_reference_crypto_funding_arbitrage/`
  - `results/2026-03-10_reference_multi_market_making/`
- Generated reference performance report: `docs/REFERENCE_PERFORMANCE.md`.
- Beginner-first web onboarding wizard at `apps/web/app/onboarding/page.tsx`.
- `make reference-bundles` and `make reference-performance` targets.

### Changed
- Simulation suite probe orders now propagate scenario strategy and expected-alpha mapping to avoid false all-reject reference runs.
- README strategy-performance callout is now generated from committed reference artifacts.
- Benchmark docs and results index updated for the new reference baseline.
- Web dashboard/home surfaces now link directly to onboarding.

### Added
- Governance and repo hygiene docs (`CONTRIBUTING`, `CODE_OF_CONDUCT`, `SECURITY`, `SUPPORT`).
- Dockerized local stack (`Dockerfile`, `docker-compose.yml`).
- GitHub Pages leaderboard export workflow.
- Release automation workflow with GitHub Release + PyPI publish support.
- Coverage workflow and CI summary artifact.
- MkDocs site configuration and benchmark/results documentation templates.
- **Operational documentation**: Incident response runbook, deployment procedures.
- **Utility scripts**: Log rotation, service health checks for operational hygiene.

### Changed
- CI workflows aligned with `src/` package layout.
- README upgraded with professional badges and comparison guidance.
- Configuration comments clarifying symbol format conventions in paper trading config.

## [0.1.0] - 2026-03-09

### Added
- Initial public PQTS codebase with modular architecture, strategy/risk modules,
  simulation tooling, and operational controls.
