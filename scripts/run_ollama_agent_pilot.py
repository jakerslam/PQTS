#!/usr/bin/env python3
"""Run a local Ollama/Kimi challenger against the PQTS agent pilot contract."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from app.agent_pilot_client import AgentPilotAPIClient  # noqa: E402
from app.ollama_agent_pilot import (  # noqa: E402
    DEFAULT_AGENT_ID,
    DEFAULT_OLLAMA_MODEL,
    OllamaPilotChallenger,
    OllamaPilotConfig,
    OllamaPilotError,
    sample_agent_context,
)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_cards(paths: list[str]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for raw_path in paths:
        payload = _load_json(Path(raw_path))
        if isinstance(payload, list):
            cards.extend(dict(item) for item in payload if isinstance(item, dict))
        elif isinstance(payload, dict):
            cards.append(dict(payload))
    return cards


def _sample_cards() -> list[dict[str, Any]]:
    example = REPO_ROOT / "src" / "research" / "agent_corpus_card_example.json"
    return [dict(_load_json(example))]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.getenv("PQTS_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL))
    parser.add_argument(
        "--base-url", default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--agent-id", default=DEFAULT_AGENT_ID)
    parser.add_argument("--quality-threshold", type=float, default=0.65)
    parser.add_argument("--context-json", help="Path to a saved /v1/agent/context JSON payload")
    parser.add_argument("--relevant-card-json", action="append", default=[], help="Card JSON file")
    parser.add_argument(
        "--counterevidence-card-json",
        action="append",
        default=[],
        help="Counterevidence card JSON file",
    )
    parser.add_argument(
        "--sample-context", action="store_true", help="Use a safe local sample context"
    )
    parser.add_argument("--api-base-url", default="http://localhost:8000")
    parser.add_argument("--api-token", default=os.getenv("PQTS_API_TOKEN", ""))
    parser.add_argument(
        "--create-intent", action="store_true", help="Create an API intent if valid"
    )
    parser.add_argument("--simulate", action="store_true", help="Simulate the created intent")
    parser.add_argument(
        "--out-dir",
        default=str(REPO_ROOT / "data" / "reports" / "ollama_agent_pilot"),
        help="Directory for the JSON run report",
    )
    return parser


def _resolve_context(args: argparse.Namespace) -> dict[str, Any]:
    if args.context_json:
        return dict(_load_json(Path(args.context_json)))
    if args.api_token:
        client = AgentPilotAPIClient(
            base_url=args.api_base_url,
            token=args.api_token,
            timeout_seconds=args.timeout_seconds,
        )
        return client.get_context(agent_id=args.agent_id)
    if args.sample_context:
        return sample_agent_context(agent_id=args.agent_id)
    raise SystemExit("provide --context-json, --api-token, or --sample-context")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    context = _resolve_context(args)
    relevant_cards = _load_cards(args.relevant_card_json)
    if args.sample_context and not relevant_cards:
        relevant_cards = _sample_cards()
    counterevidence = _load_cards(args.counterevidence_card_json)

    config = OllamaPilotConfig(
        model=args.model,
        base_url=args.base_url,
        timeout_seconds=args.timeout_seconds,
        temperature=args.temperature,
        agent_id=args.agent_id,
        quality_threshold=args.quality_threshold,
    )
    challenger = OllamaPilotChallenger(config=config)
    client = None
    if args.create_intent:
        if not args.api_token:
            raise SystemExit("--create-intent requires --api-token")
        client = AgentPilotAPIClient(
            base_url=args.api_base_url,
            token=args.api_token,
            timeout_seconds=args.timeout_seconds,
        )

    try:
        if client is None:
            result = challenger.propose(
                context,
                relevant_cards=relevant_cards,
                counterevidence=counterevidence,
            )
            created = None
            simulation = None
        else:
            result, created, simulation = challenger.propose_and_create_intent(
                client,
                context,
                relevant_cards=relevant_cards,
                counterevidence=counterevidence,
                simulate=args.simulate,
            )
    except OllamaPilotError as exc:
        print(f"Ollama challenger failed: {exc}", file=sys.stderr)
        return 2

    report = result.as_report()
    report["created_intent"] = created
    report["simulation"] = simulation
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"ollama_agent_pilot_{result.created_at.replace(':', '').replace('-', '')}_{result.prompt_hash[:12]}.json"
    report_path = out_dir / filename
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")

    print(json.dumps({k: report[k] for k in ("model", "prompt_hash", "is_valid")}, indent=2))
    if result.validation_errors:
        print("validation_errors:")
        for error in result.validation_errors:
            print(f"- {error}")
    if result.decision is not None:
        print("decision:")
        print(json.dumps(result.decision.as_intent_payload(), indent=2, sort_keys=True))
    print(f"report_path: {report_path}")
    return 0 if result.is_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
