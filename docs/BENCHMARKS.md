# Published Benchmark Baselines

Last updated: 2026-03-09 (America/Denver)

This document publishes the first reproducible PQTS benchmark baselines from committed result bundles.

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

## Notes

- These are deterministic smoke baselines for reproducibility and regression detection.
- Each bundle includes JSON/CSV outputs, charts, run metadata, and command provenance.
- Future benchmark revisions should append here instead of replacing prior baseline rows.
