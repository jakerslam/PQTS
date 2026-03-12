# Release Checklist

## Preconditions

- `main` branch green on CI
- No unresolved P0 incidents
- Changelog updated (`CHANGELOG.md`)

## Steps

1. Bump version in `pyproject.toml` if needed.
2. Add matching `## [X.Y.Z] - YYYY-MM-DD` section to `CHANGELOG.md`.
3. Run local verification:
   ```bash
   make release-readiness
   make arch-check
   make test
   python3 tools/check_public_links.py --pyproject pyproject.toml --required docs/required_public_links.txt
   python3 -m build
   python3 tools/prepare_release_artifacts.py --dist-dir dist --version X.Y.Z --git-sha "$(git rev-parse HEAD)"
   ```
4. Commit release prep changes.
5. Create and push tag:
   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```
6. Verify GitHub Release workflow completion.
7. Verify PyPI publish job completion (trusted publishing).
8. Confirm install smoke test:
   ```bash
   pip install pqts==X.Y.Z
   pqts --help
   ```

## Post-Release

- Confirm docs site and badges reflect latest release.
- Announce release with notable changes.
