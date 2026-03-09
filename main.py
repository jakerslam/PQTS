"""Compatibility entrypoint that delegates to the canonical app composition root."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if SRC.exists():
    src_str = str(SRC)
    if src_str not in sys.path:
        sys.path[:] = [src_str, *sys.path]

from app.cli import apply_cli_toggles, build_arg_parser
from app.runtime import cli_main, main

__all__ = ["apply_cli_toggles", "build_arg_parser", "main"]


if __name__ == "__main__":
    cli_main()
