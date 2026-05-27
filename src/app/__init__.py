"""Canonical app composition layer."""

from app.agent_pilot_client import AgentPilotAPIClient
from app.bootstrap import bootstrap_runtime, build_engine, build_module_registry
from app.cli import apply_cli_toggles, build_arg_parser
from app.ollama_agent_pilot import OllamaPilotChallenger, OllamaPilotConfig, PilotDecision

__all__ = [
    "AgentPilotAPIClient",
    "OllamaPilotChallenger",
    "OllamaPilotConfig",
    "PilotDecision",
    "apply_cli_toggles",
    "bootstrap_runtime",
    "build_arg_parser",
    "build_engine",
    "build_module_registry",
]
