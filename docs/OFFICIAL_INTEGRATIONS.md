# Official Integrations Index

Canonical machine-readable index:

- `config/integrations/official_integrations.json`

Validation command:

```bash
python3 tools/check_official_integrations.py --index config/integrations/official_integrations.json --max-age-days 45
```

Optional URL reachability checks:

```bash
python3 tools/check_official_integrations.py --index config/integrations/official_integrations.json --max-age-days 45 --check-urls
```

Update policy:
- Refresh `last_reviewed` when integration contracts are revalidated.
- Keep provider repo URLs and ownership metadata current.
