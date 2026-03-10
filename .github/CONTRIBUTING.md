# Contributing to PQTS

Thanks for contributing to PQTS.

## Development Setup

```bash
git clone https://github.com/jakerslam/pqts.git
cd pqts
make setup
source .venv/bin/activate
```

## Local Quality Checks

```bash
make arch-check
make test
make lint
```

Recommended focused checks before opening a PR:

```bash
python tools/check_architecture_boundaries.py
pytest tests -q
```

## Branch and PR Workflow

1. Create a branch from `main`.
2. Keep changes scoped to one feature/fix.
3. Add or update tests for behavior changes.
4. Update docs when contracts, architecture, or commands change.
5. Open a pull request using the PR template.

## Coding Standards

- Follow canonical architecture boundaries in `docs/ARCHITECTURE.md`.
- Keep runtime-safe defaults and risk controls intact.
- Prefer deterministic behavior for simulations and reporting.
- Keep backward compatibility for scripts/CLI unless explicitly changed.

## Commit Guidance

Use concise, imperative commit messages.

Examples:
- `feat: add leaderboard static publisher`
- `fix: enforce source-root path in CI lint job`
- `docs: update benchmark methodology`

## Community Expectations

By contributing, you agree to follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
