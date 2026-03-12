# Growth KPI Review

Last updated: 2026-03-11 (America/Denver)

## Scope

Track monthly traction targets and deltas for external validation signals.

Automation:

```bash
python3 scripts/compute_growth_kpi_targets.py \
  --history config/growth/community_kpi_history.json \
  --review-doc docs/GROWTH_KPI_REVIEW.md \
  --out-json docs/GROWTH_KPI_DIGEST.json
```

## Baseline Snapshot (2026-03-11)

Source: GitHub repository metrics (`jakerslam/PQTS`).

- stars: `0`
- forks: `0`
- open issues: `15`
- watchers/subscribers: `0`
- package baseline: `pqts` is published on PyPI (`v0.1.5`)

## Monthly Targets

| Month | Stars | Forks | Open Issues (quality inbound) | PyPI install signal |
| --- | ---: | ---: | ---: | --- |
| 2026-04 | >= 25 | >= 5 | >= 25 | verify first full-month install trend |
| 2026-05 | >= 60 | >= 12 | >= 40 | publish month-over-month install delta |
| 2026-06 | >= 120 | >= 25 | >= 60 | sustain positive growth trend |

Notes:

- `Open issues` target assumes active community validation and support intake, not unresolved bug accumulation.
- Install signal may be sourced from trusted package telemetry available to maintainers for month-over-month trend reporting.

## Monthly Review Template

For each month, publish:

1. Actuals vs targets for stars/forks/issues/install trend.
2. Top growth drivers (release, docs, social/community campaigns).
3. Bottlenecks (setup friction, trust gaps, integration gaps).
4. Prioritized corrective actions for the next month.

## 2026-03 Delta Log

- Baseline month initialized.
- Release + PyPI + docs workflow surfaces are active.
- Next action: publish first recurring monthly delta entry at month close.

<!-- GROWTH_KPI_DIGEST:START -->
## Automated KPI Digest

- `latest_month`: 2026-05
- `windows_evaluated`: 3
- `max_consecutive_miss_windows`: 3
- `roadmap_reprioritization_required`: true

### Recommended Actions

- Prioritize onboarding/usability conversion work over new feature expansion for next sprint.
- Require roadmap review memo linked to latest KPI digest before closing growth-related TODO items.

<!-- GROWTH_KPI_DIGEST:END -->
