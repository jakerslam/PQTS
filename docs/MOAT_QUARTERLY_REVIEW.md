# Moat Quarterly Review

Last updated: 2026-03-10 (America/Denver)

## Scope

Review parity-vs-moat delivery mix and effectiveness outcomes for the current quarter.

## Current Snapshot

- Parity P0 status: complete
- Prior target capacity split: 60% moat / 40% parity
- Updated target capacity split (Q2 2026): 65% moat / 35% parity
- Evidence sources: `docs/TODO.md`, `docs/SRS_COVERAGE_MATRIX.md`, incident and benchmark artifacts
- User-research input: `docs/USER_RESEARCH_2026_03.md`

## KPI Frame

- Adoption: net new active users and repeat usage cadence
- Retention: 30/60/90-day workflow retention for Studio and Core
- Incident impact: P0/P1 incident rate and rollback frequency
- Execution quality: reject-rate, fill-rate, slippage drift, reconciliation accuracy

## Decisions

- Increase moat allocation floor to 65% while parity SLOs remain healthy.
- Keep a 35% parity lane reserved for release polish, safety hardening, and onboarding friction removal.
- Block roadmap proposals that reduce moat share below 65% unless a documented parity incident emergency exists.

## Sign-Off

- Product owner: `jay`
- Engineering owner: `jay`
- Risk owner: `jay`
