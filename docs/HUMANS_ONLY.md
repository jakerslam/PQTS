# PQTS Humans-Only Work

Last updated: 2026-03-10 (America/Denver)

This file tracks tasks that cannot be reliably automated and require direct human ownership.

## P0 Trust + Visibility

- Create 8-10 professional screenshots and 3 short GIFs covering dashboard live view, simulation leaderboard, and paper-run workflow.
- Record 3 short demo videos (2-4 minutes each):
  - 5-minute setup
  - dashboard + leaderboard walkthrough
  - strategy tournament run
- Publish 4-5 reproducible performance result packages with config YAMLs, charts, and 2024-2026 metrics in a `results` publish bundle.
- Perform a full README narrative overhaul with visuals and competitive positioning narrative.

## P0 Trust-Surface Decisions (From March 10 Review)

- Decide release-by-release distribution truth posture: either (a) keep PyPI install path live and verified, or (b) remove/replace `pip install` claims until publication is verified.
- PyPI trusted publisher setup completed for `pqts` (`owner=jakerslam`, `repo=PQTS`, `workflow=.github/workflows/release.yml`, `environment=pypi`); first successful trusted publish shipped in `v0.1.4`.
- Approve and enforce one canonical maturity message for the active release (`alpha`/`beta`/`stable`) and remove contradictory claims from legacy docs.
- Decide and sign off the single primary public web surface for this release phase (Next.js vs legacy dashboard exposure) and publish transition messaging.
- Approve whether broad multi-market marketing claims stay live or are narrowed to only currently verified integrations in the canonical index.
- Review and sign off benchmark narrative language so historical diagnostic bundles are contextualized correctly and not framed as reference proof.
- Ensure Docker CLI is installed and runnable on maintainer workstations used for release validation (`docker --version`, `docker compose version`).
- Ensure maintainer token/permissions can dispatch Actions workflows and manage Pages settings (`workflow` + repo admin scope as needed).

## P1 Growth

- Run and publicly report 3+ month paper campaigns across crypto/equities/forex with monthly report commentary.
- Publish a weekly short-horizon trading journal (paper/live clearly labeled) with provenance-linked metrics, execution caveats, and postmortem notes.
- Publish comparison table and long-form X thread series using `docs/X_THREAD_TEMPLATE.md`.
- Submit project to discovery channels (awesome lists, communities, Show HN, etc.) and handle responses.
- Write 2-3 long-form explainers on PQTS risk/ops approach and postmortem lessons.

## P2 Community + Reputation

- Launch and actively moderate Discord/Telegram community channels.
- Execute strategic outreach (influencer engagement, issue/PR response discipline, good-first-issue curation).
- Create professional branding assets (logo + one-page site) that link docs, results, and onboarding.
- Arrange external code review/audit once sustained paper results are available.

## P0 Comparative Positioning + Product Decisions

- Own and maintain the public competitor comparison narrative (PQTS vs QuantConnect/NautilusTrader/QuantRocket/Freqtrade/Hummingbot/vectorbt/Backtrader) with dated evidence notes.
- Make and document the wedge-market decision (for example crypto-first) and approve the market-expansion gate criteria before broadening scope.
- Review and sign off benchmark-report commentary before publication so public claims match reproducible evidence.
- Define the external trust posture: what metrics are labeled `reference`, `diagnostic_only`, or `unverified` in public-facing copy.
- Record decision outcomes and sign-off in `docs/HUMAN_DECISIONS_LOG.md`.

## P1 Packaging, Pricing, and Onboarding Narrative

- Finalize human-facing packaging copy for Community, Solo Pro, Team, and Enterprise lanes.
- Own pricing-page and website messaging updates so tier language matches actual entitlements and safety constraints.
- Produce and maintain plain-language onboarding narratives/tutorial scripts for Studio users (non-technical-first audience).
- Conduct periodic user interviews (casual and professional cohorts) and convert findings into prioritization decisions.

## P1 External Cohort Validation

- Recruit and run external beginner and professional beta cohorts (non-internal participants) for each major UX release cycle.
- Publish cohort summary notes with participant mix, task-completion outcomes, and top friction points.
- Approve go/no-go readiness claims for “noob-friendly” and “pro-ready” only after external cohort evidence is reviewed.

## P0 Language and UI Direction Decisions

- Approve and record the Python-first/not-Python-only architecture policy (including target native-kernel scope).
- Decide and sign off the single primary UI path for the next release phase (web app end-state and interim fallback policy).
- Approve native-migration trigger thresholds (when to use JIT, when to move kernels to Rust, and what evidence is required).
- Approve storage-tier escalation policy (when/if to introduce additional telemetry stores beyond current operational stack).

## P0 Dominance Narrative and Market Validation

- Own and maintain the category narrative that PQTS is a trust operating system for deployment (not just another backtester/bot).
- Publish external beginner/pro validation evidence with participant mix, outcomes, and friction themes before major UX claim upgrades.
- Maintain dated competitor comparison narratives and keep public claim language aligned with verifiable evidence.
- Execute distribution/outreach campaigns (Show HN, X thread launches, community posts, partner outreach) and track outcomes.
- Set explicit monthly traction KPI targets (stars/forks/issues/downloads) and publish a recurring growth review note.
- Own canonical docs-surface migration and keep docs URLs synchronized across README, package metadata, and release notes after cutover.

## P0 10-10 Closure

- Decide and publicly announce objective graduation criteria for `alpha`, `beta`, and `stable`, then sign off each transition only when external proof, certification, and docs truth gates are satisfied.
- Enable and maintain the public docs property, release landing pages, and PyPI narrative so no public evidence surface 404s or lags the active release.
- Run recurring external beginner and professional cohorts large enough to claim category-leading usability, then publish the results with dated evidence.
- Own the crypto-first wedge narrative and refuse broader production claims until at least two tier-1 crypto venues are clearly active/certified.
- Execute the convenience/adoption layer: mobile demos, operator walkthroughs, community response discipline, and distribution campaigns that turn engineering quality into visible traction.

## P0 Remaining Gap Closure

- Publish a recurring public proof cadence (monthly benchmark bundle, cohort summary, venue-certification summary, and release evidence page) and keep the narrative synchronized across README, docs, PyPI, and release notes.
- Own the live docs property end-to-end: DNS/hosting/settings, broken-link triage, content review before each release, and immediate remediation when any public docs surface drifts or 404s.
- Operate the tier-1 crypto certification program in practice: maintain exchange accounts/credentials, run scheduled drill campaigns, review incident receipts, and sign off connector promotion from `beta` to `active/certified`.
- Conduct true beginner usability reviews focused on first-success simplicity, then approve or reject UX claims based on observed time-to-result and confusion points rather than internal intuition.
- Maintain the external trust posture: publish known limitations, respond visibly to proof gaps or incidents, and refuse marketing claims that outpace current evidence.
- Maintain a public interactive demo/sandbox and scripted walkthrough that show the guided web flow, scenario lab, and trust/provenance surfaces using current release artifacts.
