# Result Bundle: 2026-03-13_reference_multi_market_making

## Run Metadata

- Date (UTC): 2026-03-13T02:34:50.061770+00:00
- Risk profile: balanced
- Scenario count: 3
- Config snapshot: `config_paper_snapshot.yaml`

## Command

```bash
.venv/bin/python scripts/run_simulation_suite.py --config config/paper.yaml --markets crypto,equities,forex --strategies market_making --cycles-per-scenario 30 --symbols-per-market 1 --readiness-every 10 --risk-profile balanced --sleep-seconds 0.0 --out-dir results/2026-03-13_reference_multi_market_making --telemetry-log results/2026-03-13_reference_multi_market_making/simulation_events.jsonl --tca-dir results/2026-03-13_reference_multi_market_making/tca
```

## Included Artifacts

- `simulation_suite_20260313T023450012456Z.json`
- `simulation_leaderboard_20260313T023450012456Z.csv`
- `metrics_chart.svg`
- `config_paper_snapshot.yaml`
- `dataset_manifest.json`

## Key Metrics

- total_submitted=90
- total_filled=90
- total_rejected=0
- avg_quality_score=0.8246
- avg_fill_rate=1.0000
- avg_reject_rate=0.0000

- `crypto/market_making`: quality=0.82, fill=1.00, reject=0.00, submitted=30
- `equities/market_making`: quality=0.84, fill=1.00, reject=0.00, submitted=30
- `forex/market_making`: quality=0.82, fill=1.00, reject=0.00, submitted=30

## Claim Classification

- Claim class: `reference`
- Evidence source: `simulation_suite_20260313T023450012456Z.json` + `simulation_leaderboard_20260313T023450012456Z.csv`
- Non-zero fill gate: `passed`

## Notes

Reference-quality bundle intended for public reproducibility and benchmark governance.
