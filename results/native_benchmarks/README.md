# Native Execution Latency Benchmarks

Generated on: 2026-03-10 (UTC)

## Command

```bash
python3 scripts/benchmark_execution_latency.py --orders 300 --target-p95-ms 200 --out-dir results/native_benchmarks
python3 scripts/benchmark_execution_latency.py --orders 300 --target-p95-ms 200 --out-dir results/native_benchmarks --require-native
```

## Snapshot Comparison

| Mode | Artifact | p95 submit latency (ms) | Target `<200ms` |
| --- | --- | ---: | --- |
| Python fallback | `execution_latency_benchmark_20260310T175028Z.json` | 40.016 | Pass |
| Native hotpath | `execution_latency_benchmark_20260310T175237Z.json` | 14.145 | Pass |

Observed p95 speedup (`fallback / native`): **~2.83x**.

These are local in-process router benchmarks. Venue/network round-trip latency still dominates true live submit-to-ack timings.
