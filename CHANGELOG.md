# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog, and this project aims to follow
Semantic Versioning.

## [Unreleased]

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

### Changed
- CI workflows aligned with `src/` package layout.
- README upgraded with professional badges and comparison guidance.

## [0.1.0] - 2026-03-09

### Added
- Initial public PQTS codebase with modular architecture, strategy/risk modules,
  simulation tooling, and operational controls.
