# PQTS Dominance Split: SRS vs Humans

Last updated: 2026-03-11 (America/Denver)

This document converts the latest "how we beat competitors" strategy into explicit
execution classes:

- `SRS` = automatable engineering/system work.
- `human_only` = decisions, messaging, outreach, and external validation work.

## SRS execution set (already mapped and executed)

| Dominance move | Class | SRS refs | Execution status |
|---|---|---|---|
| Make safe deployment the core product (promotion + rollback + capital controls) | `SRS` | `MOAT-1, MOAT-2, MOAT-3, MOAT-4, MOAT-5, MOAT-14` | Executed in code + gates |
| Explain every live divergence with prescriptive action | `SRS` | `MOAT-1, MOAT-2, UI-014, UI-015` | Executed in order-truth + execution/risk surfaces |
| Turn benchmark publication into a product surface | `SRS` | `COMP-5, COMP-13, COMP-17, MOAT-12` | Executed with benchmark program + trust-label governance |
| Build venue execution intelligence into routing/sizing | `SRS` | `MOAT-6, MOAT-7, PMKT-7` | Executed with intelligence + adaptive routing controls |
| Deliver sub-5-minute beginner-first first success | `SRS` | `COMP-7, COMP-11, UI-004, UI-005, UI-006` | Executed via package-first + onboarding/CLI flows |
| Keep one engine with guided/pro surfaces (no product fork) | `SRS` | `COMP-6, COMP-8, COMP-9, UI-001, UI-002` | Executed via surface contracts + parity gates |
| Build constrained assistant operations instead of free-form bot control | `SRS` | `MOAT-10, MOAT-11, UI-028, UI-029` | Executed via policy-constrained operator contracts |
| Enforce proof-driven public claims with trust labels and provenance | `SRS` | `COMP-13, MOAT-12, MOAT-13, CGPT-7` | Executed with CI/docs/report claim gates |

## Human-only execution set (not automatable)

| Dominance move | Class | Why human |
|---|---|---|
| Own public category narrative ("trust operating system for deployment") | `human_only` | Positioning and market communication require human judgment |
| Run external beginner/pro cohorts and publish outcomes | `human_only` | Requires participant recruiting, interviews, and interpretation |
| Publish and maintain competitor comparison narrative with dated evidence | `human_only` | Requires editorial accountability and ongoing external review |
| Own distribution-channel execution (Show HN, Reddit, X threads, partner outreach) | `human_only` | Requires account ownership, posting, and response handling |

## Verification command set

Run the standard closure suite to verify the SRS side remains fully executed:

```bash
make full-srs-check
make dod-audit
make governance-check
```

## ChatGPT Reassessment Extraction (2026-03-11)

The March 11 reassessment is largely already assimilated. The technical concerns map
to current SRS families and do not require a new requirement family.

### Mapped to existing SRS (no new IDs required)

- Canonical web contract + route drift: `CGPT-1`, `LANG-7`, `UI-001`, `UI-013`, `UI-014`, `UI-015`
- Thin-client purity (no file/process runtime shortcuts in production paths): `CGPT-2`, `UI-019`
- Single onboarding truth across README/quickstart/package docs: `CGPT-3`, `COMP-11`, `COMP-15`
- Canonical docs surface reliability: `CGPT-4`, `COMP-1`
- Integration maturity claim parity: `CGPT-5`, `PMKT-16`
- External cohort evidence before noob/pro claims: `CGPT-6`, `COMP-18`
- Benchmark continuity with trust labels and historical integrity: `CGPT-7`, `COMP-17`, `MOAT-12`
- Version/package/release/API cohesion: `CGPT-8`, `COMP-16`

### Net-new human ownership items extracted

- Set explicit monthly traction KPIs (stars/forks/issues/downloads) and run a documented growth review cadence.
- Own canonical docs-surface migration (non-repo-tree docs URL) and keep package/release docs links synchronized after cutover.
