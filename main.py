"""Compatibility entrypoint that delegates to the canonical app composition root."""

from __future__ import annotations

import asyncio

from app.cli import apply_cli_toggles, build_arg_parser
from app.runtime import main

__all__ = ["apply_cli_toggles", "build_arg_parser", "main"]


if __name__ == "__main__":
    asyncio.run(main())
