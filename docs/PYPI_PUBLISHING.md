# PyPI Trusted Publishing Setup

This project publishes to PyPI via GitHub Actions using OpenID Connect (OIDC),
without storing long-lived API tokens.

## 1) Create PyPI Project

- Create `pqts` project on PyPI (or claim the project name if available).

## 2) Configure Trusted Publisher on PyPI

In PyPI project settings, add a trusted publisher with:

- Owner: `jakerslam`
- Repository: `PQTS`
- Workflow: `release.yml`
- Environment: `pypi`

## 3) Configure GitHub Environment

In GitHub repo settings, create environment `pypi` and optionally add:

- required reviewers
- deployment branch/tag restrictions

## 4) Publish Flow

1. Update version/changelog.
2. Tag release: `vX.Y.Z`.
3. Push tag: `git push origin vX.Y.Z`.
4. Workflow `.github/workflows/release.yml` builds distributions, creates GitHub Release, and publishes to PyPI.

## 5) Smoke Test

```bash
pip install pqts==X.Y.Z
pqts --help
```

## 6) Release Attempt Notes (2026-03-10 to 2026-03-11)

Release pipelines for tags `v0.1.0`, `v0.1.1`, and `v0.1.2` succeeded through build + GitHub release, but PyPI publish failed with:

- `invalid-publisher`: valid token, but no corresponding publisher

Observed OIDC claims from the failed run:

- `repository`: `jakerslam/PQTS`
- `workflow_ref`: `jakerslam/PQTS/.github/workflows/release.yml@refs/tags/v0.1.1`
- `environment`: `pypi`

Most recent failing run:

- workflow run id: `22934006492`
- tag: `v0.1.2`
- failing job: `publish_pypi` (`Publish to PyPI (trusted publishing)`)

Required fix on PyPI side:

1. Ensure trusted publisher is configured for **repository `jakerslam/PQTS`** (exact casing).
2. Ensure workflow path is `.github/workflows/release.yml`.
3. Ensure environment is `pypi`.
4. Ensure the trusted publisher is configured on the correct `pqts` PyPI project and not an adjacent/test project.
5. Re-run publish from a new patch tag (for example `v0.1.3`) after correcting the trusted publisher entry.

## 7) Resolution (2026-03-11)

PyPI trusted publishing is now operational.

- Successful release tag: `v0.1.4`
- Successful workflow run: `22934922518`
- Successful job: `publish_pypi`

Additional workflow hardening applied:

- `publish_pypi` now removes non-distribution files from `dist/` before upload to avoid:
  - `InvalidDistribution: Unknown distribution format: 'SHA256SUMS.txt'`

Verification:

```bash
python3 -m pip index versions pqts
# pqts (0.1.4)
```
