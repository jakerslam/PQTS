# Definition of Done (DoD)

Last updated: 2026-03-11 (America/Denver)

## Purpose

This document prevents fake progress and false check-offs.
An item is only `done` when evidence proves the implementation works and is traceable.

## Required Completion Criteria

Every engineering task must satisfy all criteria:

1. Requirement traceability:
- At least one explicit SRS requirement ID is linked in the task (`Ref: ...`).

2. Implementation reality:
- Code or configuration exists in the repository (not only plan text).

3. Verification:
- Relevant automated checks/tests were executed and passed.
- If full test execution is not possible, partial scope and blocker are documented.

4. Evidence artifact:
- The TODO line must include `Evidence:` with concrete pointers:
  - command(s) run and/or
  - generated file paths and/or
  - test names.

5. Impact scoring:
- The TODO line must include `Impact: 1-10` (system importance).
- Use consistent scoring aligned to risk/surface criticality.

6. Documentation parity:
- User-facing behavior changes update relevant docs (`README.md`, subsystem docs, or runbooks).

7. Non-regression:
- Existing behavior is preserved or intentional breakage is documented with migration notes.

## Prohibited Check-Offs

The following must remain unchecked:

- “Scaffold only” work when requirement intent is runtime behavior.
- Notes/plans without executable artifacts.
- Changes without validation evidence.
- Items blocked by external dependency unless explicitly marked blocked.

## Completion States

- `open`: not implemented.
- `in_progress`: implementation started, criteria incomplete.
- `done`: all criteria above satisfied with evidence.
- `blocked`: cannot proceed due to external dependency; blocker and next action recorded.

## Evidence Template

Use this pattern in `docs/TODO.md`:

`Evidence: <primary artifact path>; <validation command>; <result artifact/test>`

Example:

`Evidence: tools/check_codex_enforcer.py; make codex-enforcer; tests/test_check_codex_enforcer.py`
