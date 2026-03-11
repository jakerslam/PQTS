"""Order-truth evidence bundle utilities for event-intel candidate explainability."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_pretrade_evidence_bundle(
    *,
    candidate_id: str,
    strategy_id: str,
    trust_label: str,
    quote_ts: str,
    decision_ts: str,
    order_submit_ts: str,
    corroboration_source_count: int,
    corroboration_skew_seconds: float,
    causal_ok: bool,
    event_minus_quote_seconds: float,
    expected_net_ev: float,
    risk_gate_decision: str,
    gate_reason_codes: list[str],
    latency_ms: float,
) -> dict[str, Any]:
    return {
        "candidate_id": str(candidate_id),
        "strategy_id": str(strategy_id),
        "trust_label": str(trust_label),
        "created_at": _iso_utc_now(),
        "timing": {
            "quote_ts": str(quote_ts),
            "decision_ts": str(decision_ts),
            "order_submit_ts": str(order_submit_ts),
            "latency_ms": float(latency_ms),
        },
        "corroboration": {
            "source_count": int(corroboration_source_count),
            "skew_seconds": float(corroboration_skew_seconds),
        },
        "causal_alignment": {
            "causal_ok": bool(causal_ok),
            "event_minus_quote_seconds": float(event_minus_quote_seconds),
        },
        "risk_gate": {
            "decision": str(risk_gate_decision),
            "reason_codes": list(gate_reason_codes),
            "expected_net_ev": float(expected_net_ev),
        },
    }


def persist_pretrade_evidence_bundle(bundle: dict[str, Any], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def load_pretrade_evidence_bundle(path: str | Path) -> dict[str, Any] | None:
    target = Path(path)
    if not target.exists():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    return payload if isinstance(payload, dict) else None


def summarize_pretrade_evidence(bundle: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(bundle, dict):
        return None
    timing = bundle.get("timing", {}) if isinstance(bundle.get("timing"), dict) else {}
    corroboration = (
        bundle.get("corroboration", {}) if isinstance(bundle.get("corroboration"), dict) else {}
    )
    causal = (
        bundle.get("causal_alignment", {})
        if isinstance(bundle.get("causal_alignment"), dict)
        else {}
    )
    risk_gate = bundle.get("risk_gate", {}) if isinstance(bundle.get("risk_gate"), dict) else {}
    return {
        "candidate_id": str(bundle.get("candidate_id", "")),
        "strategy_id": str(bundle.get("strategy_id", "")),
        "trust_label": str(bundle.get("trust_label", "unverified")),
        "quote_ts": str(timing.get("quote_ts", "")),
        "decision_ts": str(timing.get("decision_ts", "")),
        "order_submit_ts": str(timing.get("order_submit_ts", "")),
        "latency_ms": float(timing.get("latency_ms", 0.0) or 0.0),
        "source_count": int(corroboration.get("source_count", 0) or 0),
        "skew_seconds": float(corroboration.get("skew_seconds", 0.0) or 0.0),
        "causal_ok": bool(causal.get("causal_ok", False)),
        "event_minus_quote_seconds": float(causal.get("event_minus_quote_seconds", 0.0) or 0.0),
        "risk_gate_decision": str(risk_gate.get("decision", "")),
        "risk_gate_reason_codes": [str(x) for x in list(risk_gate.get("reason_codes", []))],
        "expected_net_ev": float(risk_gate.get("expected_net_ev", 0.0) or 0.0),
    }
