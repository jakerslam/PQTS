# Result Bundle: 2026-03-09_multi_market_market_making_short

## Run Metadata

- Date (UTC): 2026-03-09T18:07:50.585697+00:00
- Risk profile: balanced
- Scenario count: 3
- Config snapshot: `config_paper_snapshot.yaml`

## Command

```bash
python3 scripts/run_simulation_suite.py --markets crypto,equities,forex --strategies market_making --cycles-per-scenario 8 --readiness-every 4 --out-dir /Users/jay/Document (Lcl)/Coding/PQTS/results/2026-03-09_multi_market_market_making_short --telemetry-log /Users/jay/Document (Lcl)/Coding/PQTS/results/2026-03-09_multi_market_market_making_short/simulation_events.jsonl --tca-dir /Users/jay/Document (Lcl)/Coding/PQTS/results/2026-03-09_multi_market_market_making_short/tca --sleep-seconds 0.0 --symbols-per-market 1 --risk-profile balanced
```

## Included Artifacts

- `simulation_suite_20260309T180750584558Z.json`
- `simulation_leaderboard_20260309T180750584558Z.csv`
- `metrics_chart.svg`
- `config_paper_snapshot.yaml`
- `dataset_manifest.json`
- `simulation_events.jsonl`
- `tca/` (per-run execution telemetry)

## Key Metrics

- `crypto/market_making`: quality=0.00, fill=0.00, reject=1.00, priority=2.00
- `equities/market_making`: quality=0.00, fill=0.00, reject=1.00, priority=2.00
- `forex/market_making`: quality=0.00, fill=0.00, reject=1.00, priority=2.00

## Claim Classification

- Claim class: `diagnostic_only`
- Evidence source: `simulation_suite_20260309T180750584558Z.json` + `simulation_leaderboard_20260309T180750584558Z.csv`

## Notes

This bundle is isolated from shared telemetry logs for clean reproducibility.
