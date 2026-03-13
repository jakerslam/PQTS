# Reference Performance

Last generated (UTC): 2026-03-13T02:34:47.458853+00:00

This file is generated from `results/reference_performance_latest.json`.

## Highlight

- Best bundle by quality: `2026-03-13_reference_crypto_trend_following`
- Metrics: quality `0.8535`, fill `1.0000`, reject `0.0000`
- Artifacts: [bundle](../results/2026-03-13_reference_crypto_trend_following/README.md), [csv](../results/2026-03-13_reference_crypto_trend_following/simulation_leaderboard_20260313T023448292806Z.csv), [report](../results/2026-03-13_reference_crypto_trend_following/simulation_suite_20260313T023448292806Z.json)

## Bundle Table

| Bundle | Markets | Strategy | Submitted | Filled | Rejected | Quality | Fill | Reject |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `2026-03-13_reference_crypto_funding_arbitrage` | `crypto` | `funding_arbitrage` | 36 | 36 | 0 | 0.8199 | 1.0000 | 0.0000 |
| `2026-03-13_reference_crypto_trend_following` | `crypto` | `trend_following` | 36 | 36 | 0 | 0.8535 | 1.0000 | 0.0000 |
| `2026-03-13_reference_multi_market_making` | `crypto,equities,forex` | `market_making` | 90 | 90 | 0 | 0.8246 | 1.0000 | 0.0000 |

## Regeneration

```bash
python3 scripts/publish_reference_bundles.py --config config/paper.yaml --out-root results
python3 scripts/render_reference_performance.py
```
