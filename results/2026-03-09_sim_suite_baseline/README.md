# PQTS Baseline Simulation Result (2026-03-09)

This is a reproducible public baseline bundle generated from the current `main` branch.

## Run Metadata

- Date (UTC): 2026-03-09T17:57:23Z
- Commit: generated post-`469b842`
- Config: `config/paper.yaml`
- Risk profile: `balanced`

## Command

```bash
python3 scripts/run_simulation_suite.py \
  --markets crypto \
  --strategies market_making \
  --cycles-per-scenario 8 \
  --readiness-every 4 \
  --out-dir data/reports \
  --sleep-seconds 0.0 \
  --symbols-per-market 1 \
  --risk-profile balanced
```

## Included Artifacts

- `simulation_suite_20260309T175723522900Z.json`
- `simulation_leaderboard_20260309T175723522900Z.csv`
- `quality_reject_chart.svg`

## Key Metrics

- `avg_quality_score`: 0.0
- `avg_fill_rate`: 0.0
- `avg_reject_rate`: 1.0
- `optimization_priority`: 2.0

This baseline is intentionally retained as a deterministic reference point for future improvements.
