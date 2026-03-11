# Codex Enforcer Protocol

Last updated: 2026-03-11 (America/Denver)

## Objective

Force execution discipline and prevent checkbox theater.

This protocol is mandatory for every coding session.
It is anchored to [Definition of Done](/Users/jay/Document (Lcl)/Coding/PQTS/docs/DEFINITION_OF_DONE.md).

## Mandatory Read Order (Every Session)

1. `AGENTS.md`
2. `docs/CODEX_COMPLIANCE.md`
3. `docs/CODEX_ENFORCER.md` (this file)
4. `docs/DEFINITION_OF_DONE.md`
5. `docs/ARCHITECTURE.md`
6. `docs/IMPLEMENTATION_DIRECTION.md`

## Session Preflight Checklist

Before implementation:

1. Confirm the task has `Ref:` IDs from `docs/SRS.md`.
2. Define acceptance check(s) before coding.
3. Identify concrete evidence artifacts to attach to the TODO item.

## Execution Rules

1. No item is marked done without `Evidence:` in `docs/TODO.md`.
2. No item is marked done without `Impact: 1-10` in `docs/TODO.md`.
3. Evidence must point to real repository artifacts and runnable checks.
4. If work is partial, mark as `in_progress` or leave unchecked.
5. If blocked by external dependency, mark blocked and document the blocker.

## Enforcement Commands

Run these before marking tasks done:

1. `make codex-enforcer`
2. `make assimilation-66-71-check`
3. Targeted tests for changed tooling/docs checks.

## Failure Policy

If enforcement fails:

1. Do not check off task items.
2. Fix the failure.
3. Re-run enforcement.
