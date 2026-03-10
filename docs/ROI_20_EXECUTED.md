# Top-20 ROI Moves Executed

Date: 2026-03-10

Goal alignment:
- Faster path from zero-to-first-success for beginners
- Stronger operational tooling for professional users
- One coherent command surface (`pqts`) for both groups

## Executed Moves

1. Added shared operator-experience strategy catalog (`src/app/operator_experience.py`).
2. Added shared risk-profile catalog (`src/app/operator_experience.py`).
3. Added shared block-reason explainer map (`src/app/operator_experience.py`).
4. Added `pqts doctor` preflight checks.
5. Added `pqts doctor --fix` auto-create workspace data directories.
6. Added `pqts quickstart` beginner-safe dry-run orchestration plan.
7. Added `pqts quickstart --execute` end-to-end onboarding run.
8. Added `pqts strategies list` command.
9. Added `pqts strategies explain <strategy>` command.
10. Added `pqts risk list` command.
11. Added `pqts risk recommend` command.
12. Added `pqts status reports` command.
13. Added `pqts status leaderboard` command.
14. Added `pqts status readiness` command.
15. Added `pqts notify test --channel stdout|telegram|discord`.
16. Added `pqts explain block <reason_code>` command.
17. Added `pqts artifacts latest` command.
18. Added `make doctor` shortcut.
19. Added `make onboard` shortcut.
20. Added `make status` shortcut.

## Why this is high ROI

- Beginner usability: a single guided path (`doctor` + `quickstart`) removes setup ambiguity.
- Pro depth: status, readiness, artifact inspection, and channel checks are now first-class CLI operations.
- Coherence: strategy/risk/explain logic centralized in one reusable module.
- Testability: command behavior is fully unit-tested in `tests/test_first_success_cli.py`.
