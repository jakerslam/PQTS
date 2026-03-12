# Official Integrations Index

Canonical machine-readable index:

- `config/integrations/official_integrations.json`
- `config/integrations/official_integration_requirements.json`

Validation command:

```bash
python3 tools/check_official_integrations.py \
  --index config/integrations/official_integrations.json \
  --requirements config/integrations/official_integration_requirements.json \
  --max-age-days 45
```

Optional URL reachability checks:

```bash
python3 tools/check_official_integrations.py --index config/integrations/official_integrations.json --max-age-days 45 --check-urls
```

Update policy:
- Refresh `last_reviewed` when integration contracts are revalidated.
- Keep provider repo URLs and ownership metadata current.
- Use status progression: `experimental` -> `beta` -> `active`/`certified` -> `deprecated`.
- Every index entry must include readiness fields:
  - `paper_ok`
  - `latency_budget`
  - `reliability_budget`
  - `incident_profile`
- Promotion to `paper`/`canary`/`live` is stage-gated by adapter maturity requirements.
- Release gating validates required venue maturity + certification evidence:

```bash
python3 tools/check_release_readiness.py --policy config/release/release_readiness_policy.json
```
