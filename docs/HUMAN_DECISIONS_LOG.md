# PQTS Human Decisions Log

Last updated: 2026-03-10 (America/Denver)

This file captures non-automatable decisions that gate roadmap and go-to-market execution.

## Decision 001: Primary Wedge Market

- Status: `approved`
- Owner: `jay`
- Decision date: `2026-03-10`
- Effective date: `2026-03-10`

### Context

Choose one initial market wedge to dominate before broad expansion.

### Options

- `crypto_first`
- `equities_first`
- `forex_first`

### Selected Option

- `crypto_first`

### Expansion Gates (must pass before enabling additional market classes)

- Execution quality gate thresholds met for reference scenarios.
- Reconciliation accuracy SLO sustained for defined window.
- Incident/error-budget criteria sustained for defined window.

### Sign-Off

- Product owner: `jay`
- Engineering owner: `jay`
- Risk owner: `jay`

## Decision 002: Public Trust Label Policy

- Status: `approved`
- Owner: `jay`
- Decision date: `2026-03-10`
- Effective date: `2026-03-10`

### Context

Define which public result class labels are permitted and how they appear in external materials.

### Label Definitions

- `reference`: Meets benchmark quality gate and provenance requirements.
- `diagnostic_only`: Fails one or more quality gates; excluded from reference summaries.
- `unverified`: Claim lacks reproducible artifact-level evidence.

### Publishing Rules

- Performance claims must cite artifact paths and provenance logs.
- `diagnostic_only` and `unverified` labels must be displayed in public benchmark/report views.
- Marketing copy cannot elevate `diagnostic_only` or `unverified` results to reference claims.

### Sign-Off

- Product owner: `jay`
- Research owner: `jay`
- Compliance owner: `jay`

## Decision 003: Primary UI Architecture Path

- Status: `approved`
- Owner: `jay`
- Decision date: `2026-03-10`
- Effective date: `2026-03-10`

### Context

Choose one primary operator UI architecture for the next release phase and define deprecation policy for secondary surfaces.

### Options

- `web_primary` (TypeScript web app + FastAPI control plane)
- `dash_primary_interim` (Dash-only interim while web app matures)

### Selected Option

- `web_primary` (FastAPI control plane + TypeScript web app end-state, Dash interim fallback until cutover gates pass)

### Constraints

- Must avoid dual-framework ambiguity for core operator workflows.
- Must preserve risk/incident controls and parity with control-plane contracts.

### Sign-Off

- Product owner: `jay`
- Engineering owner: `jay`
- Ops owner: `jay`

## Decision 004: Native Kernel Migration Scope and Triggers

- Status: `approved`
- Owner: `jay`
- Decision date: `2026-03-10`
- Effective date: `2026-03-10`

### Context

Define where native kernels are allowed and what evidence is required before migrating Python modules.

### Candidate Kernel Domains

- orderbook sequencing
- deterministic event replay
- routing/fill hot path

### Trigger Policy

- JIT-first for vectorizable numeric kernels.
- Native migration only after measured bottleneck evidence exceeds approved thresholds.

### Selected Policy

- `python_first_hotpath_native`:
  - Keep strategy/research/control logic Python-first.
  - Require measured bottleneck evidence before native migration.
  - Use thresholds in `config/native/migration_policy.json` as default trigger contract.
  - Require reproducible before/after benchmark artifacts for each migration.

### Sign-Off

- Engineering owner: `jay`
- Performance owner: `jay`
- Risk owner: `jay`
