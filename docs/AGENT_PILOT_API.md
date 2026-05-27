# Agent Pilot API + SDK

Last updated: 2026-05-27 (America/Denver)

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
- Local LLM/agent challengers may propose intents, but they do not place orders and do not bypass simulation, stage gates, kill switches, or `RiskAwareRouter.submit_order()`.

## Local Ollama/Kimi Challenger

PQTS ships a bounded Ollama challenger in `app.ollama_agent_pilot`. It builds the required fixed-block pilot context:

1. `SYSTEM_FACTS`
2. `CURRENT_STATE`
3. `RELEVANT_CARDS`
4. `COUNTEREVIDENCE`
5. `DECISION_TEMPLATE`

The model must return one JSON object with the strict pilot fields:

```json
{
  "action": "hold",
  "strategy_id": "example_strategy",
  "rationale": "Evidence is insufficient for promotion.",
  "supporting_card_ids": ["card_id"],
  "current_metrics": {},
  "gate_checks": {},
  "risk_impact": {}
}
```

Only these actions are accepted: `promote_to_paper`, `promote_to_live_canary`, `promote_to_live`, `hold`, `demote`, `kill`. Any unsupported action, malformed JSON, missing field, or empty support list fails closed and creates no intent.

Run a local Kimi 2.6 smoke test without touching the API:

```bash
python3 scripts/run_ollama_agent_pilot.py \
  --sample-context \
  --model kimi-k2.6:cloud \
  --timeout-seconds 60
```

To let a valid model response create and simulate an intent through the API:

```bash
PQTS_API_TOKEN=operator-token python3 scripts/run_ollama_agent_pilot.py \
  --api-base-url http://localhost:8000 \
  --agent-id ollama-kimi-pilot \
  --model kimi-k2.6:cloud \
  --create-intent \
  --simulate
```

The runner writes a JSON report under `data/reports/ollama_agent_pilot/` containing the model, prompt hash, raw response, validation errors, decision payload, created intent, and simulation response. It never executes intents.
