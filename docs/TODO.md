# PQTS Execution TODO (Parity vs Moat)

Last updated: 2026-03-10 (America/Denver)

Execution policy:
- Run sections top-to-bottom by default.
- `Parity` items are admission-fee work and block most `Moat` items.
- Once `Parity P0` is complete, enforce capacity split target: 60% `moat`, 40% remaining `parity`.

Legend:
- `ROI`: `very_high`, `high`, `medium`
- `Type`: `engineering` or `human_only`
- `Track`: `parity` or `moat`
- `Ref`: SRS requirement IDs

## 00. Completed Foundation (Pinned)

- [x] Docs/metadata link gate in CI and release (`ROI: very_high`, `Type: engineering`, `Track: parity`, `Ref: COMP-1`)
- [x] Semantic release integrity baseline (`ROI: very_high`, `Type: engineering`, `Track: parity`, `Ref: COMP-2`)
- [x] Benchmark classification baseline (`ROI: very_high`, `Type: engineering`, `Track: parity`, `Ref: COMP-3`)
- [x] First-success CLI baseline (`ROI: very_high`, `Type: engineering`, `Track: parity`, `Ref: COMP-11`)
- [x] Monthly report pipeline baseline (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: COMP-5`)

## 01. Parity Track (Admission Fee, Dependency Ordered)

### P0 Trust and Reproducibility Baseline

- [x] Implement golden dataset/version governance checks (`ROI: very_high`, `Type: engineering`, `Track: parity`, `Ref: COMP-4`)
- [x] Implement reference strategy pack standard and baseline diffing (`ROI: very_high`, `Type: engineering`, `Track: parity`, `Ref: COMP-5`, `Depends: COMP-4`)
- [x] Enforce claim-evidence linting in docs/reports/benchmark pages (`ROI: very_high`, `Type: engineering`, `Track: parity`, `Ref: COMP-13`, `Depends: COMP-4, COMP-5`)
- [x] Add official integration index and CI freshness validation (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: PMKT-1`)
- [x] Standardize CLI machine output/error contracts and exit-code behavior (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: PMKT-9`)
- [x] Ship read-only-first + guided authenticated setup docs flow (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: PMKT-10`)
- [x] Add wallet-mode example packs + CI smoke tests (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: PMKT-11`, `Depends: PMKT-10`)
- [x] Promote at least one benchmark scenario from `diagnostic_only` to `reference` (`ROI: very_high`, `Type: engineering`, `Track: parity`, `Ref: COMP-3`, `Depends: COMP-4, COMP-5`)

### P1 Product Coherence and Surface Contracts

- [x] Enforce one engine / two surface contract (`ROI: very_high`, `Type: engineering`, `Track: parity`, `Ref: COMP-6`)
- [x] Remove mixed runtime ambiguity and lock one UI execution path per release phase (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: LANG-6`, `Depends: COMP-6`)
- [x] Complete FastAPI-centered control-plane contract for active UIs (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: LANG-7`, `Depends: COMP-6, LANG-6`)
- [x] Add Studio/Core action parity and traceability tests (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: COMP-9`, `Depends: COMP-6, LANG-7`)
- [x] Add UI migration cutover gates and rollback tests (`ROI: medium`, `Type: engineering`, `Track: parity`, `Ref: LANG-11`, `Depends: COMP-9`)

### P2 Venue Adapter Hardening

- [x] Implement explicit read-only vs authenticated client states (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: PMKT-2`)
- [x] Implement signature-type + funder binding contracts (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: PMKT-3`, `Depends: PMKT-2`)
- [x] Implement API credential lifecycle and audit logging (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: PMKT-4`, `Depends: PMKT-2`)
- [x] Add approval/allowance preflight blocking controls (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: PMKT-5`, `Depends: PMKT-3`)
- [x] Standardize canonical order lifecycle and batch operation schema (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: PMKT-6`, `Depends: PMKT-2`)
- [x] Harden websocket coverage, reconnect, and disconnect safety controls (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: PMKT-7`, `Depends: PMKT-6`)
- [x] Add local/remote signer interface + builder-mode scopes (`ROI: medium`, `Type: engineering`, `Track: parity`, `Ref: PMKT-8`, `Depends: PMKT-4`)
- [x] Add non-custodial hybrid settlement invariants and typed-signature checks (`ROI: medium`, `Type: engineering`, `Track: parity`, `Ref: PMKT-12`)
- [x] Add complementary-outcome fee symmetry tests and reporting (`ROI: medium`, `Type: engineering`, `Track: parity`, `Ref: PMKT-13`, `Depends: PMKT-12`)
- [x] Enforce contract deployment registry and audit artifact gates (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: PMKT-14`, `Depends: PMKT-12`)

### P3 Runtime and Data Plane Hardening

- [x] Harden typed config/API/manifest boundaries (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: LANG-5`)
- [x] Implement local analytical data-plane standard (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: LANG-4`)
- [x] Enforce storage-tier boundary policy checks (`ROI: medium`, `Type: engineering`, `Track: parity`, `Ref: LANG-8`, `Depends: LANG-4`)
- [x] Add mode-specific cycle/refresh SLO telemetry and reports (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: LANG-9`)
- [x] Ship native hot-path extension boundary skeleton (`ROI: medium`, `Type: engineering`, `Track: parity`, `Ref: LANG-2`)
- [x] Add trigger instrumentation for JIT-first vs native migration (`ROI: medium`, `Type: engineering`, `Track: parity`, `Ref: LANG-3`, `Depends: LANG-2, LANG-9`)
- [x] Add native artifact release matrix and metadata (`ROI: medium`, `Type: engineering`, `Track: parity`, `Ref: LANG-10`, `Depends: LANG-2`)

## 02. Moat Track (Dominance, Dependency Ordered)

### M0 Deployment Trust Operating System

- [x] Build per-order truth graph (`ROI: very_high`, `Type: engineering`, `Track: moat`, `Ref: MOAT-1`)
- [x] Build divergence diagnosis engine with prescriptive actions (`ROI: very_high`, `Type: engineering`, `Track: moat`, `Ref: MOAT-2`, `Depends: MOAT-1`)
- [x] Implement promotion state machine (`backtest->paper->shadow->canary->live`) (`ROI: very_high`, `Type: engineering`, `Track: moat`, `Ref: MOAT-3`, `Depends: COMP-6, COMP-8`)
- [x] Auto-generate promotion memos + rollback contracts (`ROI: high`, `Type: engineering`, `Track: moat`, `Ref: MOAT-4`, `Depends: MOAT-3`)
- [x] Enforce stage-aware capital allocation policies (`ROI: very_high`, `Type: engineering`, `Track: moat`, `Ref: MOAT-5`, `Depends: MOAT-3`)

### M1 Execution Intelligence Network

- [x] Build venue execution-intelligence feature pipeline (`ROI: very_high`, `Type: engineering`, `Track: moat`, `Ref: MOAT-6`, `Depends: PMKT-7`)
- [x] Integrate adaptive routing/sizing/throttling from execution intelligence (`ROI: very_high`, `Type: engineering`, `Track: moat`, `Ref: MOAT-7`, `Depends: MOAT-6`)

### M2 Unified Casual-Pro Product Surface

- [x] Implement one canonical strategy object across Studio/Core (`ROI: high`, `Type: engineering`, `Track: moat`, `Ref: MOAT-8`, `Depends: COMP-7, COMP-8, COMP-12`)
- [x] Enforce bidirectional UI<->CLI transparency and parity gates (`ROI: high`, `Type: engineering`, `Track: moat`, `Ref: MOAT-9`, `Depends: MOAT-8, COMP-9`)

### M3 Policy-Constrained AI and Incident Operations

- [x] Implement constrained autonomous operator permissions (`propose/simulate/execute`) (`ROI: high`, `Type: engineering`, `Track: moat`, `Ref: MOAT-10`, `Depends: COMP-14, LANG-7`)
- [x] Implement incident copilot with safe rollback assist (`ROI: high`, `Type: engineering`, `Track: moat`, `Ref: MOAT-11`, `Depends: MOAT-1, MOAT-10`)

### M4 Proof and Governance Flywheel

- [x] Ship scheduled proof-as-product artifact pipeline (`ROI: very_high`, `Type: engineering`, `Track: moat`, `Ref: MOAT-12`, `Depends: COMP-4, COMP-5, COMP-13, MOAT-1`)
- [x] Enforce trust classification gates for all public metrics (`ROI: high`, `Type: engineering`, `Track: moat`, `Ref: MOAT-13`, `Depends: COMP-13, MOAT-12`)
- [x] Implement team governance workflows and capital controls (`ROI: very_high`, `Type: engineering`, `Track: moat`, `Ref: MOAT-14`, `Depends: MOAT-3, COMP-14`)
- [x] Add roadmap governance for parity/moat allocation and quarterly efficacy review (`ROI: high`, `Type: engineering`, `Track: moat`, `Ref: MOAT-15`)
- [x] Add periodic competitor-source revalidation workflow (`ROI: medium`, `Type: engineering`, `Track: moat`, `Ref: MOAT-16`)

## 02b. High-ROI Coverage Closure Sprint (2026-03-10)

- [x] Enforce Studio casual UX contract gates in CI (`ROI: very_high`, `Type: engineering`, `Track: parity`, `Ref: COMP-7`)
- [x] Enforce Core professional contract gates in CI (`ROI: very_high`, `Type: engineering`, `Track: parity`, `Ref: COMP-8`)
- [x] Implement wedge-first market scope policy + runtime enforcement (`ROI: very_high`, `Type: engineering`, `Track: parity`, `Ref: COMP-10`)
- [x] Persist template-run config/code artifacts and diffs for first-success workflows (`ROI: very_high`, `Type: engineering`, `Track: parity`, `Ref: COMP-12`)
- [x] Encode Community/Solo Pro/Team/Enterprise tier safety policy with live preconditions (`ROI: very_high`, `Type: engineering`, `Track: parity`, `Ref: COMP-14`)
- [x] Enforce Python-first stack direction via explicit policy file checks (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: LANG-1`)
- [x] Add native migration trigger policy thresholds + priority module validation (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: LANG-3`)
- [x] Enforce single primary UI framework coherence between stack policy and surface contracts (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: LANG-6`)
- [x] Enforce source-reliability taxonomy for external claims and trust labels (`ROI: high`, `Type: engineering`, `Track: moat`, `Ref: LANG-12, PMKT-15, MOAT-13`)
- [x] Enforce moat-vs-parity governance and quarterly review freshness gates (`ROI: high`, `Type: engineering`, `Track: moat`, `Ref: MOAT-15`)

## 02c. Visibility Polish (Open, High ROI)

- [x] Fix README Visual Tour media paths so screenshots/GIFs render correctly in GitHub and package contexts (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: COMP-11, COMP-13`)
- [x] Add one highlighted performance callout sourced from latest reference result bundle (for example Sharpe and max drawdown) with explicit bundle link (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: COMP-3, COMP-5, COMP-13`)
- [x] Add a README architecture/performance paragraph that documents Rust hot-path kernels and links [docs/NATIVE_HOTPATH.md](/Users/jay/Document%20(Lcl)/Coding/PQTS/docs/NATIVE_HOTPATH.md) (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: LANG-2, LANG-10, COMP-13`)
- [x] Publish a quick native-vs-python benchmark artifact under `results/` (for example `sum_notional` throughput multiplier) with reproducible command + environment metadata (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: LANG-3, LANG-10, COMP-13`)
- [x] Add `make native` target to expose maturin-based local native build/install workflow (`ROI: medium`, `Type: engineering`, `Track: parity`, `Ref: LANG-2, LANG-10`)
- [ ] Trigger first public PyPI release and GitHub Pages leaderboard export, then publish both links in README/docs (`ROI: very_high`, `Type: human_only`, `Track: parity`, `Ref: COMP-2, COMP-5, MOAT-12`)

## 02d. Nunchi Agent-CLI Assimilation Sprint (2026-03-10)

- [x] Implement authenticated SSE channel surface with heartbeat and account scoping (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: NCLI-1, AHF-5`)
- [x] Add skill package discovery + raw URL export commands and seed `skills/*/SKILL.md` packages (`ROI: high`, `Type: engineering`, `Track: parity`, `Ref: NCLI-2, DXR-6`)
- [x] Implement nightly bounded self-improvement review runner with reversible override generation (`ROI: high`, `Type: engineering`, `Track: moat`, `Ref: NCLI-3, MOAT-12`)
- [x] Add deployment run-mode environment contract and validation gates (`ROI: medium`, `Type: engineering`, `Track: parity`, `Ref: NCLI-4`)
- [x] Standardize autonomous memory/journal/judge artifacts and promotion linkage (`ROI: medium`, `Type: engineering`, `Track: moat`, `Ref: NCLI-5`)

## 03. Human-Only Parallel Lane

- [x] Finalize and sign blocking decisions in [docs/HUMAN_DECISIONS_LOG.md](/Users/jay/Document%20(Lcl)/Coding/PQTS/docs/HUMAN_DECISIONS_LOG.md) (`ROI: very_high`, `Type: human_only`, `Track: parity`, `Ref: COMP-10, LANG-6, LANG-3, COMP-14`)
- [x] Finalize packaging and pricing narrative for Community/Solo Pro/Team/Enterprise (`ROI: high`, `Type: human_only`, `Track: parity`, `Ref: COMP-14`)
- [x] Approve trust-label policy language for public artifacts (`ROI: high`, `Type: human_only`, `Track: moat`, `Ref: MOAT-13`)
- [x] Run monthly user interviews for casual and professional cohorts and feed roadmap deltas (`ROI: high`, `Type: human_only`, `Track: moat`, `Ref: COMP-7, COMP-8, MOAT-8`)
- [x] Publish quarterly moat efficacy review and adjust parity/moat capacity target (`ROI: high`, `Type: human_only`, `Track: moat`, `Ref: MOAT-15`)

## 04. Tracking and Issue Hygiene

- [x] Create or refresh GitHub issues for all open `PMKT-*` and `MOAT-*` requirements with SRS links (`ROI: high`, `Type: engineering`, `Track: parity`)
- [x] Close issues only when merged code includes tests and explicit `Ref` coverage in PR description (`ROI: high`, `Type: engineering`, `Track: parity`)
