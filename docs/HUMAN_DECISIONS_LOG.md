# PQTS Human Decisions Log

Last updated: 2026-03-10 (America/Denver)

This file captures non-automatable decisions that gate roadmap and go-to-market execution.

## Decision 001: Primary Wedge Market

- Status: `pending`
- Owner: `TBD`
- Decision date: `TBD`
- Effective date: `TBD`

### Context

Choose one initial market wedge to dominate before broad expansion.

### Options

- `crypto_first`
- `equities_first`
- `forex_first`

### Selected Option

- `TBD`

### Expansion Gates (must pass before enabling additional market classes)

- Execution quality gate thresholds met for reference scenarios.
- Reconciliation accuracy SLO sustained for defined window.
- Incident/error-budget criteria sustained for defined window.

### Sign-Off

- Product owner: `TBD`
- Engineering owner: `TBD`
- Risk owner: `TBD`

## Decision 002: Public Trust Label Policy

- Status: `pending`
- Owner: `TBD`
- Decision date: `TBD`
- Effective date: `TBD`

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

- Product owner: `TBD`
- Research owner: `TBD`
- Compliance owner: `TBD`

## Decision 003: Primary UI Architecture Path

- Status: `pending`
- Owner: `TBD`
- Decision date: `TBD`
- Effective date: `TBD`

### Context

Choose one primary operator UI architecture for the next release phase and define deprecation policy for secondary surfaces.

### Options

- `web_primary` (TypeScript web app + FastAPI control plane)
- `dash_primary_interim` (Dash-only interim while web app matures)

### Selected Option

- `TBD`

### Constraints

- Must avoid dual-framework ambiguity for core operator workflows.
- Must preserve risk/incident controls and parity with control-plane contracts.

### Sign-Off

- Product owner: `TBD`
- Engineering owner: `TBD`
- Ops owner: `TBD`

## Decision 004: Native Kernel Migration Scope and Triggers

- Status: `pending`
- Owner: `TBD`
- Decision date: `TBD`
- Effective date: `TBD`

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

- `TBD`

### Sign-Off

- Engineering owner: `TBD`
- Performance owner: `TBD`
- Risk owner: `TBD`
