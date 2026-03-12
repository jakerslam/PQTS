# Agent Pilot API + SDK

Last updated: 2026-03-11 (America/Denver)

This document describes the canonical agent-pilot control-plane endpoints and the Python SDK wrapper shipped in `app.agent_pilot_client`.

## API Surface

- `GET /v1/agent/context`
- `GET /v1/agent/policies/{agent_id}`
- `PUT /v1/agent/policies/{agent_id}`
- `POST /v1/agent/intents`
- `GET /v1/agent/intents/{intent_id}`
- `POST /v1/agent/intents/{intent_id}/simulate`
- `POST /v1/agent/intents/{intent_id}/execute`
- `GET /v1/agent/receipts/{receipt_id}`
- `GET /v1/agent/hooks`
- `POST /v1/agent/hooks`
- `DELETE /v1/agent/hooks/{hook_id}`

## Python SDK

```python
from app.agent_pilot_client import AgentPilotAPIClient

viewer = AgentPilotAPIClient(base_url="http://localhost:8000", token="viewer-token")
operator = AgentPilotAPIClient(base_url="http://localhost:8000", token="operator-token")

context = viewer.get_context()
agent_id = context["agent_id"]

operator.upsert_policy(
    agent_id=agent_id,
    capabilities={"read": True, "propose": True, "simulate": True, "execute": True, "hooks_manage": True},
)

intent = viewer.create_intent(
    action="promote_to_paper",
    strategy_id="trend_following",
    rationale="paper readiness preserved",
    supporting_card_ids=["card_a"],
    current_metrics={"fill_rate": 0.93, "reject_rate": 0.01},
    gate_checks={"paper_days": 45},
    risk_impact={"delta_var_pct": 0.3},
)

intent_id = intent["intent"]["intent_id"]
viewer.simulate_intent(intent_id=intent_id)
operator.execute_intent(intent_id=intent_id)
```

## Guardrails

- Execute remains operator-gated and policy-gated.
- Simulation pass is required before execute.
- Hook creation is allowlist-constrained and secret values are fingerprinted (not stored raw).
- Default policy starts with `execute=false` and fails closed.
