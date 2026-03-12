# Monthly User Research Review (2026-03)

Last updated: 2026-03-12 (America/Denver)

Validation metadata:
- `release_window: 2026-03`
- `external_beginner_participants: 0`
- `external_pro_participants: 0`
- `internal_proxy_participants: 2`
- `release_gate_status: blocked_pending_external_cohort`

## Objective

Capture one monthly feedback cycle for both target cohorts and convert findings into concrete roadmap deltas.

## Cohort Coverage

1. Casual cohort (internal proxy run)
- Method: first-success journey replay (`pqts demo`, `pqts backtest momentum`, `pqts paper start`) with docs-first onboarding pass.
- Primary lens: time-to-first-meaningful-run, UI clarity, perceived safety.

2. Professional cohort (operator interview)
- Method: direct operator backlog session focused on speed, architecture clarity, and promotion-to-live trust controls.
- Primary lens: execution discipline, reproducibility, governance, and deployment confidence.

## Top Findings

1. Visual proof and benchmark callouts materially affect trust at first glance.
2. Native hotpath status must be explicit at runtime; silent Python fallback in low-latency modes creates ambiguity.
3. Users need one obvious path for web surface evolution (web-primary) without breaking current Dash operations.
4. Artifact provenance remains a critical differentiator for professional adoption.

## Roadmap Deltas Added This Cycle

1. Added low-latency runtime profile + required-native guard for live canary mode.
2. Added reproducible execution latency benchmark artifacts (`results/native_benchmarks/`).
3. Fixed README visual media pathing for GitHub/PyPI render reliability.
4. Added explicit reference-bundle performance callout in README.
5. Finalized packaging/trust/governance decisions in `docs/HUMAN_DECISIONS_LOG.md`.

## Next Cycle Questions (2026-04)

1. Does first-success flow reach meaningful paper output in under 5 minutes on clean machine setup?
2. Are trust labels (`reference`, `diagnostic_only`, `unverified`) understood by new users without extra explanation?
3. Are live-canary operators satisfied with low-latency guard behavior and rollback visibility?
