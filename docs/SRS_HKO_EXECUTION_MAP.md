# SRS HKO Execution Map

Last updated: 2026-03-11 (America/Denver)

Scope:
- `HKO-1..HKO-8`

This map defines implementation lanes for the hanakoxbt OSINT/event-intel requirement family.

## Lane 1: Event-Intel Ingestion and Trigger Guards

Ref:
- `HKO-1`
- `HKO-2`
- `HKO-3`
- `HKO-4`

Primary components:
- `src/execution/event_intel_gates.py`
- `config/strategy/assimilation_hko_defaults.json`

Acceptance artifacts:
- Corroboration gate decision traces (source count + skew metrics)
- Causal alignment and anti-lookahead reason codes
- Explicit stale-quote and stale-event hold decisions

## Lane 2: External Provider Boundary and Health

Ref:
- `HKO-5`

Primary components:
- `src/integrations/signal_provider_adapter.py`

Acceptance artifacts:
- Read-only provider normalization output
- Entitlement/schema-drift health state telemetry
- Blocked write-intent key rejection tests

## Lane 3: Evidence Bundle and Explainability

Ref:
- `HKO-6`
- `HKO-7`

Primary components:
- `src/execution/order_truth.py`
- `services/api/ops_data.py`
- `apps/web/app/dashboard/execution/page.tsx`
- `tools/check_claim_evidence_links.py`

Acceptance artifacts:
- Persisted pre-trade evidence bundle with traceable timing/risk fields
- API order-truth payload with `evidence_bundle` summary
- UI evidence panel with trust label and gate details
- Claim-evidence link validation pass

## Lane 4: Capacity/Decay Control

Ref:
- `HKO-8`

Primary components:
- `src/risk/edge_decay_monitor.py`

Acceptance artifacts:
- Deterministic hold/tighten/pause decisions from load-decay metrics
- Auto-tighten recommendation output and test coverage

## Operational Defaults

- [config/strategy/assimilation_hko_defaults.json](/Users/jay/Document%20(Lcl)/Coding/PQTS/config/strategy/assimilation_hko_defaults.json)
