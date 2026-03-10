# Result Bundle: 2026-03-09_crypto_funding_arbitrage_short

## Run Metadata

- Date (UTC): 2026-03-09T18:07:49.742703+00:00
- Risk profile: balanced
- Scenario count: 1
- Config snapshot: `config_paper_snapshot.yaml`

## Command

```bash
python3 scripts/run_simulation_suite.py --markets crypto --strategies funding_arbitrage --cycles-per-scenario 12 --readiness-every 4 --out-dir /Users/jay/Document (Lcl)/Coding/PQTS/results/2026-03-09_crypto_funding_arbitrage_short --telemetry-log /Users/jay/Document (Lcl)/Coding/PQTS/results/2026-03-09_crypto_funding_arbitrage_short/simulation_events.jsonl --tca-dir /Users/jay/Document (Lcl)/Coding/PQTS/results/2026-03-09_crypto_funding_arbitrage_short/tca --sleep-seconds 0.0 --symbols-per-market 1 --risk-profile balanced
```

## Included Artifacts

- `simulation_suite_20260309T180749741503Z.json`
- `simulation_leaderboard_20260309T180749741503Z.csv`
- `metrics_chart.svg`
- `config_paper_snapshot.yaml`
- `dataset_manifest.json`
- `simulation_events.jsonl`
- `tca/` (per-run execution telemetry)

## Key Metrics

- `crypto/funding_arbitrage`: quality=0.00, fill=0.00, reject=1.00, priority=2.00

## Claim Classification

- Claim class: `diagnostic_only`
- Evidence source: `simulation_suite_20260309T180749741503Z.json` + `simulation_leaderboard_20260309T180749741503Z.csv`

## Notes

This bundle is isolated from shared telemetry logs for clean reproducibility.
