# Release Checklist

## Preconditions

- `main` branch green on CI
- No unresolved P0 incidents
- Changelog updated (`CHANGELOG.md`)

## Steps

1. Bump version in `pyproject.toml` if needed.
2. Run local verification:
   ```bash
   make arch-check
   make test
   python3 tools/check_public_links.py --pyproject pyproject.toml --required docs/required_public_links.txt
   ```
3. Commit release prep changes.
4. Create and push tag:
   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```
5. Verify GitHub Release workflow completion.
6. Verify PyPI publish job completion (trusted publishing).
7. Confirm install smoke test:
   ```bash
   pip install pqts==X.Y.Z
   pqts --help
   ```

## Post-Release

- Confirm docs site and badges reflect latest release.
- Announce release with notable changes.
