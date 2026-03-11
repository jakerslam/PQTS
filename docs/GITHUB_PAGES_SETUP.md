# GitHub Pages Setup

Last updated: 2026-03-10 (America/Denver)

## Current Status

Pages publish workflow is wired (`.github/workflows/publish-leaderboard.yml`) with
`actions/configure-pages@v5` using `enablement: true`. This enables first-run site
creation when repository settings permit GitHub Actions Pages deployments.

## One-Time Repository Setup (Owner/Admin)

1. Open repository settings: `Settings -> Pages`.
2. Set source to **GitHub Actions**.
3. Save settings and confirm Pages is enabled for the repository.
4. Ensure workflow permissions allow `pages:write` and `id-token:write`.

## After Enablement

1. Re-run workflow: `Publish Docs Site` (workflow dispatch), or push any docs change.
2. Verify deployment URL appears in workflow summary.
3. Confirm URL resolves: `https://jakerslam.github.io/PQTS/`.

If repository permissions still block Pages creation, the workflow now uploads
`docs-site-fallback` as a run artifact so docs builds remain accessible while
owner/admin settings are being finalized.

## Fallback Artifact

Until Pages is enabled, the generated leaderboard remains available in-repo:

- `docs/leaderboard/index.html`
