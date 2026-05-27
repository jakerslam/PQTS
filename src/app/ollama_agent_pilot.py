"""Ollama-backed challenger for the agent pilot decision contract.

This module intentionally lives in the app/control-plane layer. It turns a
local model response into a structured pilot intent candidate; it never places
orders and never bypasses the existing simulate/execute gates.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.agent_pilot_client import AgentPilotAPIClient

ALLOWED_PILOT_ACTIONS: tuple[str, ...] = (
    "demote",
    "hold",
    "kill",
    "promote_to_live",
    "promote_to_live_canary",
    "promote_to_paper",
)

REQUIRED_DECISION_FIELDS: tuple[str, ...] = (
    "action",
    "strategy_id",
    "rationale",
    "supporting_card_ids",
    "current_metrics",
    "gate_checks",
    "risk_impact",
)

DEFAULT_OLLAMA_MODEL = "kimi-k2.6:cloud"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_AGENT_ID = "ollama-kimi-pilot"

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.IGNORECASE | re.DOTALL)


class OllamaPilotError(RuntimeError):
    """Raised when the local model transport cannot produce a response."""


@dataclass(frozen=True, slots=True)
class PilotDecision:
    """Machine-validated pilot decision compatible with `/v1/agent/intents`."""

    action: str
    strategy_id: str
    rationale: str
    supporting_card_ids: tuple[str, ...]
    current_metrics: dict[str, Any]
    gate_checks: dict[str, Any]
    risk_impact: dict[str, Any]

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "PilotDecision":
        errors = validate_pilot_decision(payload)
        if errors:
            raise ValueError("; ".join(errors))
        return cls(
            action=str(payload["action"]).strip().lower(),
            strategy_id=str(payload["strategy_id"]).strip(),
            rationale=str(payload["rationale"]).strip(),
            supporting_card_ids=tuple(str(item).strip() for item in payload["supporting_card_ids"]),
            current_metrics=dict(payload["current_metrics"]),
            gate_checks=dict(payload["gate_checks"]),
            risk_impact=dict(payload["risk_impact"]),
        )

    def as_intent_payload(self, *, agent_id: str | None = None) -> dict[str, Any]:
        payload = {
            "action": self.action,
            "strategy_id": self.strategy_id,
            "rationale": self.rationale,
            "supporting_card_ids": list(self.supporting_card_ids),
            "current_metrics": dict(self.current_metrics),
            "gate_checks": dict(self.gate_checks),
            "risk_impact": dict(self.risk_impact),
        }
        if agent_id:
            payload["agent_id"] = agent_id
        return payload


@dataclass(frozen=True, slots=True)
class OllamaPilotConfig:
    """Runtime knobs for a local Ollama-backed pilot challenger."""

    model: str = field(default_factory=lambda: os.getenv("PQTS_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL))
    base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
    )
    timeout_seconds: float = 60.0
    temperature: float = 0.0
    agent_id: str = DEFAULT_AGENT_ID
    quality_threshold: float = 0.65


@dataclass(frozen=True, slots=True)
class OllamaPilotResult:
    """Full result envelope for auditability and reproducibility."""

    model: str
    prompt: str
    raw_response: str
    provider_response: dict[str, Any]
    validation_errors: tuple[str, ...]
    decision: PilotDecision | None
    relevant_card_ids: tuple[str, ...]
    counterevidence_card_ids: tuple[str, ...]
    created_at: str

    @property
    def is_valid(self) -> bool:
        return self.decision is not None and not self.validation_errors

    @property
    def prompt_hash(self) -> str:
        return hashlib.sha256(self.prompt.encode("utf-8")).hexdigest()

    def as_report(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "created_at": self.created_at,
            "prompt_hash": self.prompt_hash,
            "is_valid": self.is_valid,
            "validation_errors": list(self.validation_errors),
            "decision": self.decision.as_intent_payload() if self.decision else None,
            "relevant_card_ids": list(self.relevant_card_ids),
            "counterevidence_card_ids": list(self.counterevidence_card_ids),
            "raw_response": self.raw_response,
            "provider_response": dict(self.provider_response),
        }


OllamaTransport = Callable[[dict[str, Any], OllamaPilotConfig], Mapping[str, Any]]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


def _normalize_card_id(card: Mapping[str, Any]) -> str:
    return str(card.get("card_id", "")).strip()


def card_quality_score(card: Mapping[str, Any]) -> float:
    quality = card.get("quality", {})
    if not isinstance(quality, Mapping):
        return 0.0
    try:
        return float(quality.get("quality_score", 0.0))
    except (TypeError, ValueError):
        return 0.0


def card_quality_threshold(card: Mapping[str, Any], *, fallback: float) -> float:
    quality = card.get("quality", {})
    if not isinstance(quality, Mapping):
        return fallback
    try:
        return float(quality.get("min_quality_for_retrieval", fallback))
    except (TypeError, ValueError):
        return fallback


def filter_retrievable_cards(
    cards: Iterable[Mapping[str, Any]],
    *,
    quality_threshold: float = 0.65,
) -> list[dict[str, Any]]:
    """Keep only schema-style cards above their retrieval quality threshold."""

    retrievable: list[dict[str, Any]] = []
    for card in cards:
        card_dict = dict(card)
        effective_threshold = max(
            float(quality_threshold),
            card_quality_threshold(card_dict, fallback=quality_threshold),
        )
        if card_quality_score(card_dict) >= effective_threshold:
            retrievable.append(card_dict)
    return retrievable


def validate_pilot_decision(payload: Mapping[str, Any]) -> list[str]:
    """Validate the strict pilot decision contract before creating an intent."""

    errors: list[str] = []
    for field_name in REQUIRED_DECISION_FIELDS:
        if field_name not in payload:
            errors.append(f"missing required field: {field_name}")

    action = str(payload.get("action", "")).strip().lower()
    if action not in ALLOWED_PILOT_ACTIONS:
        errors.append(f"unsupported action: {action or '<empty>'}")

    strategy_id = str(payload.get("strategy_id", "")).strip()
    if not strategy_id:
        errors.append("strategy_id must be non-empty")

    rationale = str(payload.get("rationale", "")).strip()
    if not rationale:
        errors.append("rationale must be non-empty")

    supporting = payload.get("supporting_card_ids", [])
    if not isinstance(supporting, Sequence) or isinstance(supporting, (str, bytes)):
        errors.append("supporting_card_ids must be a non-empty array")
    else:
        normalized_supporting = [str(item).strip() for item in supporting]
        if not any(normalized_supporting):
            errors.append("supporting_card_ids must be a non-empty array")

    for object_field in ("current_metrics", "gate_checks", "risk_impact"):
        if object_field in payload and not isinstance(payload.get(object_field), Mapping):
            errors.append(f"{object_field} must be an object")

    return errors


def _extract_json_from_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    try:
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    for match in _JSON_FENCE_RE.finditer(text):
        try:
            payload = json.loads(match.group(1).strip())
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            continue

    start = text.find("{")
    if start < 0:
        raise ValueError("model response did not contain a JSON object")

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                payload = json.loads(text[start : index + 1])
                if not isinstance(payload, dict):
                    raise ValueError("model JSON response was not an object")
                return payload
    raise ValueError("model response contained an incomplete JSON object")


def _extract_ollama_content(response: Mapping[str, Any]) -> str:
    message = response.get("message")
    if isinstance(message, Mapping):
        content = message.get("content")
        if isinstance(content, str):
            return content
    response_text = response.get("response")
    if isinstance(response_text, str):
        return response_text
    raise OllamaPilotError("Ollama response did not contain message.content or response")


def build_pilot_prompt(
    context: Mapping[str, Any],
    *,
    relevant_cards: Iterable[Mapping[str, Any]] = (),
    counterevidence: Iterable[Mapping[str, Any]] = (),
    quality_threshold: float = 0.65,
) -> str:
    """Build the fixed-block prompt required by the pilot corpus protocol."""

    relevant_card_rows = [dict(card) for card in relevant_cards]
    counterevidence_rows = [dict(card) for card in counterevidence]
    current_state = context.get("current_state", {})
    system_facts = {
        "system_facts": context.get("system_facts", {}),
        "policy": context.get("policy", {}),
    }
    decision_template = {
        "action": f"one of {list(ALLOWED_PILOT_ACTIONS)}",
        "strategy_id": "existing strategy id from CURRENT_STATE when available",
        "rationale": "quant rationale grounded in card evidence and gate state",
        "supporting_card_ids": ["card_id_1"],
        "current_metrics": {"metric_name": "latest value used for the decision"},
        "gate_checks": {"gate_name": "pass/fail/value and reason"},
        "risk_impact": {"risk_metric": "estimated delta and constraint impact"},
    }
    instructions = {
        "role": "PQTS agent-pilot challenger",
        "hard_constraints": [
            "Propose only the allowed pilot actions.",
            "Do not place orders, request order placement, or route around risk controls.",
            "Order entry, if any later exists, must flow only through RiskAwareRouter.submit_order().",
            "Kill switches, drawdown limits, leverage limits, and stage gates are authoritative.",
            "Never skip documented stages: backtest -> paper -> live_canary -> live.",
            "If live/canary evidence is missing or hard-gate state is unknown, choose hold.",
            "If evidence quality is insufficient, choose hold and explain the missing evidence.",
            "Output one JSON object only, with no Markdown.",
        ],
        "quality_threshold": quality_threshold,
    }
    return "\n\n".join(
        [
            "SYSTEM_FACTS\n" + _json_dumps(system_facts),
            "CURRENT_STATE\n" + _json_dumps(current_state),
            "RELEVANT_CARDS\n" + _json_dumps(relevant_card_rows),
            "COUNTEREVIDENCE\n" + _json_dumps(counterevidence_rows),
            "DECISION_TEMPLATE\n" + _json_dumps(decision_template),
            "MODEL_INSTRUCTIONS\n" + _json_dumps(instructions),
        ]
    )


def build_ollama_chat_payload(prompt: str, config: OllamaPilotConfig) -> dict[str, Any]:
    return {
        "model": config.model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a bounded quant trading pilot reviewer. "
                    "Return strict JSON and default to hold when evidence is weak."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": config.temperature},
    }


def post_ollama_chat(payload: dict[str, Any], config: OllamaPilotConfig) -> Mapping[str, Any]:
    url = config.base_url.rstrip("/") + "/api/chat"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise OllamaPilotError(f"Ollama HTTP {exc.code}: {error_body}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise OllamaPilotError(f"Ollama request failed: {exc}") from exc

    try:
        response_json = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise OllamaPilotError("Ollama returned non-JSON response") from exc
    if not isinstance(response_json, Mapping):
        raise OllamaPilotError("Ollama returned non-object JSON response")
    return response_json


class OllamaPilotChallenger:
    """Bounded local-model challenger for pilot recommendations."""

    def __init__(
        self,
        config: OllamaPilotConfig | None = None,
        transport: OllamaTransport | None = None,
    ) -> None:
        self.config = config or OllamaPilotConfig()
        self.transport = transport or post_ollama_chat

    def propose(
        self,
        context: Mapping[str, Any],
        *,
        relevant_cards: Iterable[Mapping[str, Any]] = (),
        counterevidence: Iterable[Mapping[str, Any]] = (),
    ) -> OllamaPilotResult:
        accepted_relevant = filter_retrievable_cards(
            relevant_cards,
            quality_threshold=self.config.quality_threshold,
        )
        accepted_counterevidence = filter_retrievable_cards(
            counterevidence,
            quality_threshold=self.config.quality_threshold,
        )
        prompt = build_pilot_prompt(
            context,
            relevant_cards=accepted_relevant,
            counterevidence=accepted_counterevidence,
            quality_threshold=self.config.quality_threshold,
        )
        payload = build_ollama_chat_payload(prompt, self.config)
        provider_response = dict(self.transport(payload, self.config))
        raw_response = _extract_ollama_content(provider_response)
        validation_errors: list[str] = []
        decision: PilotDecision | None = None
        try:
            decision_payload = _extract_json_from_text(raw_response)
            validation_errors.extend(validate_pilot_decision(decision_payload))
            if not validation_errors:
                decision = PilotDecision.from_payload(decision_payload)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            validation_errors.append(str(exc))

        return OllamaPilotResult(
            model=self.config.model,
            prompt=prompt,
            raw_response=raw_response,
            provider_response=provider_response,
            validation_errors=tuple(validation_errors),
            decision=decision,
            relevant_card_ids=tuple(
                card_id
                for card_id in (_normalize_card_id(card) for card in accepted_relevant)
                if card_id
            ),
            counterevidence_card_ids=tuple(
                card_id
                for card_id in (_normalize_card_id(card) for card in accepted_counterevidence)
                if card_id
            ),
            created_at=_utc_now_iso(),
        )

    def propose_and_create_intent(
        self,
        client: AgentPilotAPIClient,
        context: Mapping[str, Any],
        *,
        relevant_cards: Iterable[Mapping[str, Any]] = (),
        counterevidence: Iterable[Mapping[str, Any]] = (),
        simulate: bool = False,
    ) -> tuple[OllamaPilotResult, dict[str, Any] | None, dict[str, Any] | None]:
        result = self.propose(
            context,
            relevant_cards=relevant_cards,
            counterevidence=counterevidence,
        )
        if result.decision is None:
            return result, None, None
        agent_id = (
            str(context.get("agent_id", self.config.agent_id)).strip() or self.config.agent_id
        )
        created = client.create_intent(**result.decision.as_intent_payload(agent_id=agent_id))
        simulation = None
        if simulate:
            intent = created.get("intent", {})
            intent_id = str(intent.get("intent_id", "")).strip()
            if not intent_id:
                raise RuntimeError("agent API did not return intent.intent_id")
            simulation = client.simulate_intent(intent_id=intent_id)
        return result, created, simulation


def sample_agent_context(*, agent_id: str = DEFAULT_AGENT_ID) -> dict[str, Any]:
    """Small safe context for local smoke tests when the API is not running."""

    return {
        "agent_id": agent_id,
        "system_facts": {
            "hard_rules": [
                "orders_must_flow_via_risk_aware_router",
                "kill_switch_and_risk_limits_non_bypassable",
                "promotion_stage_skips_disallowed_by_gate_policy",
            ],
            "allowed_actions": list(ALLOWED_PILOT_ACTIONS),
        },
        "current_state": {
            "account": {"account_id": "paper-main", "equity": 100000.0, "currency": "USD"},
            "risk_state": {
                "kill_switch_active": False,
                "daily_loss_pct": 0.003,
                "max_drawdown_pct": 0.09,
                "max_leverage": 1.2,
            },
            "sync_health": {"degraded_count": 0, "all_clear": True},
            "promotion_stages": [
                {
                    "strategy_id": "mm_toxicity_filter",
                    "stage": "backtest",
                    "updated_at": _utc_now_iso(),
                }
            ],
        },
        "policy": {
            "agent_id": agent_id,
            "capabilities": {
                "read": True,
                "propose": True,
                "simulate": True,
                "execute": False,
                "hooks_manage": True,
            },
            "max_pending_intents": 20,
            "risk_budget_pct": 2.0,
            "allowed_markets": ["crypto"],
            "allowed_actions": list(ALLOWED_PILOT_ACTIONS),
        },
    }
