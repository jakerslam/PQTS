"""Canonical app composition layer."""

from app.bootstrap import bootstrap_runtime, build_engine, build_module_registry
from app.cli import apply_cli_toggles, build_arg_parser

__all__ = [
    "apply_cli_toggles",
    "bootstrap_runtime",
    "build_arg_parser",
    "build_engine",
    "build_module_registry",
]
