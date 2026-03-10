# Reproducible Results

This folder stores published reproducible result bundles.

Each bundle should include:

- exact commands used
- config files and overrides
- input dataset manifest/checksum
- output artifacts (report JSON/CSV, charts)
- summary metrics (Sharpe, drawdown, return, reject-rate)

## Naming Convention

`YYYY-MM-DD_<campaign_or_suite_name>/`

Example:

`2026-03-09_sim_suite_baseline/`

## Current Public Bundles

- `2026-03-09_sim_suite_baseline/`
- `2026-03-09_crypto_market_making_short/`
- `2026-03-09_crypto_funding_arbitrage_short/`
- `2026-03-09_multi_market_market_making_short/`
- `2026-03-10_reference_market_making/`
- `native_benchmarks/` (execution-latency benchmark artifacts for Python fallback vs native hotpath)

All current bundles contain:
- run command in per-bundle `README.md`
- config snapshot (`config_paper_snapshot.yaml`)
- dataset manifest (`dataset_manifest.json`)
- metrics outputs (`simulation_suite_*.json`, `simulation_leaderboard_*.csv`)
- at least one chart artifact (`metrics_chart.svg` or `quality_reject_chart.svg`)
- claim classification + evidence links in per-bundle `README.md`
