# Published Benchmark Baselines

Last updated: 2026-03-10 (America/Denver)

This document publishes the first reproducible PQTS benchmark baselines from committed result bundles.

## Reference Bundle Update (2026-03-10)

Reference bundles are now generated with non-zero fill gates enforced by
`scripts/publish_reference_bundles.py`.

```bash
python3 scripts/publish_reference_bundles.py --config config/paper.yaml --out-root results
python3 scripts/render_reference_performance.py
```

| Bundle | Scenarios | Artifact | Metrics (quality/fill/reject) |
|---|---:|---|---|
| `results/2026-03-10_reference_crypto_trend_following` | 1 | `simulation_leaderboard_20260310T195908561273Z.csv` | `0.83 / 1.00 / 0.00` |
| `results/2026-03-10_reference_crypto_funding_arbitrage` | 1 | `simulation_leaderboard_20260310T195909288775Z.csv` | `0.82 / 1.00 / 0.00` |
| `results/2026-03-10_reference_multi_market_making` | 3 | `simulation_leaderboard_20260310T195910268392Z.csv` | `0.82 / 1.00 / 0.00` |

Machine-readable summary:
- `results/reference_performance_latest.json`
- `docs/REFERENCE_PERFORMANCE.md` (generated report)

## Environment Snapshot

- OS: Darwin 25.2.0 (`arm64`)
- CPU: Apple M1 (8 cores)
- RAM: 8 GB
- Python: 3.13.1
- Config: `config/paper.yaml`
- Risk profile: `balanced`

## Baseline Commands

```bash
python3 scripts/run_simulation_suite.py --markets crypto --strategies market_making --cycles-per-scenario 8 --readiness-every 4 --out-dir results/2026-03-09_sim_suite_baseline --sleep-seconds 0.0 --symbols-per-market 1 --risk-profile balanced
python3 scripts/run_simulation_suite.py --markets crypto --strategies funding_arbitrage --cycles-per-scenario 12 --readiness-every 4 --out-dir results/2026-03-09_crypto_funding_arbitrage_short --telemetry-log results/2026-03-09_crypto_funding_arbitrage_short/simulation_events.jsonl --tca-dir results/2026-03-09_crypto_funding_arbitrage_short/tca --sleep-seconds 0.0 --symbols-per-market 1 --risk-profile balanced
python3 scripts/run_simulation_suite.py --markets crypto,equities,forex --strategies market_making --cycles-per-scenario 8 --readiness-every 4 --out-dir results/2026-03-09_multi_market_market_making_short --telemetry-log results/2026-03-09_multi_market_market_making_short/simulation_events.jsonl --tca-dir results/2026-03-09_multi_market_market_making_short/tca --sleep-seconds 0.0 --symbols-per-market 1 --risk-profile balanced
```

## Published Baseline Bundles

| Bundle | Scenarios | Artifact | Metrics (quality/fill/reject/priority) |
|---|---:|---|---|
| `results/2026-03-09_sim_suite_baseline` | 1 | `simulation_leaderboard_20260309T175723522900Z.csv` | `0.00 / 0.00 / 1.00 / 2.00` |
| `results/2026-03-09_crypto_funding_arbitrage_short` | 1 | `simulation_leaderboard_20260309T180749741503Z.csv` | `0.00 / 0.00 / 1.00 / 2.00` |
| `results/2026-03-09_multi_market_market_making_short` | 3 | `simulation_leaderboard_20260309T180750584558Z.csv` | `0.00 / 0.00 / 1.00 / 2.00` (crypto, equities, forex) |

## Monthly Automated Report Pipeline

Use the monthly generator to publish machine-readable and human-readable benchmark packs:

```bash
python3 scripts/generate_monthly_report.py --month 2026-03 --results-dir results --out-dir data/reports/monthly
```

Generated artifacts:
- `data/reports/monthly/2026-03/monthly_report_2026-03.json`
- `data/reports/monthly/2026-03/monthly_report_2026-03.html`
- `data/reports/monthly/2026-03/monthly_report_2026-03.pdf`
- `data/reports/monthly/2026-03/monthly_report_2026-03_equity_curve.svg`

Quality classification policy:
- `result_class: reference`: non-zero fill rate and reject rate <= `0.40` across evaluated attribution rows.
- `result_class: diagnostic_only`: any quality gate failure (for example zero fill or reject rate above threshold).
- `result_class: unverified`: artifacts missing minimum provenance/evidence fields and therefore excluded from benchmark claims.
- `diagnostic_only` and `unverified` results are excluded from reference benchmark summaries.

## Benchmark Provenance Standard

Update and maintain the canonical benchmark provenance log:

```bash
python3 scripts/update_benchmark_provenance_log.py --month 2026-03 --results-dir results --out data/reports/provenance/benchmark_provenance.jsonl
```

Each provenance row records:
- `strategy_version` (git SHA used for benchmark publication)
- `dataset_version` (explicit dataset/version tag or config-derived fallback)
- `environment_hash` (deterministic hash of runtime+artifact fingerprint)
- `run_timestamp` (benchmark run timestamp from bundle metadata)

## Result Bundle Governance and Reference Pack Diffing

Validate bundle governance constraints and generate reference-pack artifacts:

```bash
python3 tools/check_result_bundle_governance.py --results-dir results --index-out data/reports/reference_packs/index.json --diff-out data/reports/reference_packs/diff.json
```

Generated artifacts:
- `data/reports/reference_packs/index.json` (canonical strategy-pack index)
- `data/reports/reference_packs/diff.json` (latest-vs-previous delta by market/strategy)

Validation rules include:
- required bundle artifacts (`README.md`, `config_paper_snapshot.yaml`, `dataset_manifest.json`, `simulation_suite_*.json`)
- optional CSV leaderboard (`simulation_leaderboard_*.csv`) when present
- dataset-manifest schema checks
- minimum reference-pack count gate

Claim-evidence gate:

```bash
python3 tools/check_claim_evidence.py
```

## Notes

- These are deterministic smoke baselines for reproducibility and regression detection.
- Each bundle includes JSON/CSV outputs, charts, run metadata, and command provenance.
- Future benchmark revisions should append here instead of replacing prior baseline rows.
