# Streamlit Deprecation Milestones

Last updated: 2026-03-09

## Objective
Retire the legacy Streamlit surface only after Next.js web parity is verifiably green for key operator workflows.

## Hard Gates
- Parity checks pass for core metrics (`equity`, `drawdown`, risk status, order/fill counts) via `analytics.dashboard_parity`.
- Frontend/backend contract tests pass for tool-renderer mappings and graph node event envelopes.
- Playwright smoke tests pass for login, dashboard load, assistant flow, and risk page rendering.
- No critical API/web SLO alerts over the rolling validation window.

## Milestones
1. Dual-run phase (current)
- Streamlit and Next.js run in parallel.
- Daily parity report artifacts collected.
- Gating owner: Engineering.

2. Restricted Streamlit phase
- Streamlit becomes read-only for operators.
- New features ship only to `apps/web`.
- Rollback path: re-enable Streamlit write actions if parity/SLO fails.

3. Cutover phase
- Default entrypoint switches to Next.js.
- Streamlit marked deprecated in docs and CLI output.
- 14-day stabilization window with incident review.

4. Retirement phase
- Remove Streamlit from production deployment manifests.
- Keep archive branch/tag for historical reproducibility.
- Freeze date recorded in changelog and release notes.

## Exit Checklist
- [ ] All parity gates green for 14 consecutive days.
- [ ] No unresolved P0/P1 incidents tied to web migration.
- [ ] Operator team signoff captured.
- [ ] Streamlit routes removed from deployment profile.
