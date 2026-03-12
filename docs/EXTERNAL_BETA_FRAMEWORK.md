# External Beta Cohort Framework

Last updated: 2026-03-12 (America/Denver)

## Goal

Provide a repeatable path to validate PQTS with real external beginners and professionals, then feed measured findings into SRS-backed roadmap updates.

## Canonical Artifacts

- Cohort registry: `data/validation/external_beta/cohort_registry.json`
- Monthly findings: `docs/USER_RESEARCH_2026_03.md` (rolling monthly update)
- Validation gate: `tools/check_external_beta_framework.py`
- Release-readiness gate: `tools/check_release_readiness.py`

## Cohort Model

Each release window records:

- `release_window` (`YYYY-MM`)
- `status` (`planned`, `active`, or `completed`)
- `external_beginner_participants`
- `external_pro_participants`
- `internal_proxy_participants`
- channels used for recruitment and follow-up
- concrete next actions for the following cycle

## Minimum Process

1. Register the upcoming window in `cohort_registry.json`.
2. Run sessions for both cohorts:
   - beginners: onboarding + first-success flow
   - professionals: execution/risk/promotion triage flow
3. Publish the monthly findings summary with outcome metrics and roadmap deltas.
4. Keep `release_window` counts synchronized between registry and monthly research doc.

## Release Gate Thresholds

The release readiness policy (`config/release/release_readiness_policy.json`) currently enforces:

- current release-window cohort status must be `active` or `completed`
- `external_beginner_participants >= 1`
- `external_pro_participants >= 1`

If these thresholds are not met, tag-based release publishing is blocked.

## Promotion of This Framework

This framework becomes a hard promotion gate once external participants are consistently non-zero for two consecutive release windows.
