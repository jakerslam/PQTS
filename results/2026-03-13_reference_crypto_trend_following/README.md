# Result Bundle: 2026-03-13_reference_crypto_trend_following

## Run Metadata

- Date (UTC): 2026-03-13T02:34:48.340903+00:00
- Risk profile: balanced
- Scenario count: 1
- Config snapshot: `config_paper_snapshot.yaml`

## Command

```bash
.venv/bin/python scripts/run_simulation_suite.py --config config/paper.yaml --markets crypto --strategies trend_following --cycles-per-scenario 36 --symbols-per-market 1 --readiness-every 12 --risk-profile balanced --sleep-seconds 0.0 --out-dir results/2026-03-13_reference_crypto_trend_following --telemetry-log results/2026-03-13_reference_crypto_trend_following/simulation_events.jsonl --tca-dir results/2026-03-13_reference_crypto_trend_following/tca
```

## Included Artifacts

- `simulation_suite_20260313T023448292806Z.json`
- `simulation_leaderboard_20260313T023448292806Z.csv`
- `metrics_chart.svg`
- `config_paper_snapshot.yaml`
- `dataset_manifest.json`

## Key Metrics

- total_submitted=36
- total_filled=36
- total_rejected=0
- avg_quality_score=0.8535
- avg_fill_rate=1.0000
- avg_reject_rate=0.0000

- `crypto/trend_following`: quality=0.85, fill=1.00, reject=0.00, submitted=36

## Claim Classification

- Claim class: `reference`
- Evidence source: `simulation_suite_20260313T023448292806Z.json` + `simulation_leaderboard_20260313T023448292806Z.csv`
- Non-zero fill gate: `passed`

## Notes

Reference-quality bundle intended for public reproducibility and benchmark governance.
