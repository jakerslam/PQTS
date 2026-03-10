# Pricing And Packaging

Last updated: 2026-03-10 (America/Denver)

## Positioning
PQTS is packaged as a B2B quant execution and research platform for:
- Prop trading firms
- Signal funds
- Family-office systematic teams

Final narrative direction (approved):
- Community: easiest safe path to reproducible paper-trading outcomes.
- Solo Pro: fastest path from research to controlled live canary.
- Team: governance, promotion controls, and shared operational accountability.
- Enterprise: compliance-grade deployment and integration depth.

## Tiers (Safety Baseline)
1. Community (paper-only)
- Local-first onboarding and template workflows
- Paper campaign orchestration with readiness gates
- No live enablement

2. Solo Pro
- Multi-market routing (crypto/equities/forex)
- Reliability failover and ops alerting
- Live enablement only after paper-readiness + operator acknowledgment

3. Team
- Shared controls for promotion/canary operations
- Expanded strategy/session envelopes and governance workflow support
- Live enablement only after paper-readiness + operator acknowledgment

4. Enterprise
- Dedicated deployment and controls review
- Custom integrations (OMS/exchange adapters)
- Compliance artifacts and audit exports
- Live enablement only after paper-readiness + operator acknowledgment

## Add-Ons
- Strategy marketplace rev-share: 5-15%
- Execution advisory and venue onboarding
- Dedicated quant pilot services

## Packaging Principles
- No strategy claims without measured evidence.
- Promotion eligibility requires documented paper-readiness pass.
- Live canary access only after hard-gate acceptance.
- Tier capabilities are encoded in `config/entitlements/tier_policy.json`.

## Public Copy Guardrails

- Never market `diagnostic_only` or `unverified` outcomes as proof of live readiness.
- Keep Community copy focused on learning + safety, not profit guarantees.
- Keep Solo Pro/Team/Enterprise copy focused on controls, reproducibility, and governance.
- Every quantitative claim in web/docs must link to a reproducible artifact bundle.

## Self-Serve Signup Requirements
- Tenant onboarding with workspace key
- Billing + entitlement checks by tier
- Feature flags:
  - `multi_market_enabled`
  - `live_canary_enabled`
  - `ops_alert_exports`
