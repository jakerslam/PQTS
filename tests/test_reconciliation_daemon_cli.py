"""Tests for scripts/run_reconciliation_daemon.py helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "scripts" / "run_reconciliation_daemon.py"
SPEC = importlib.util.spec_from_file_location("run_reconciliation_daemon", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_parse_aliases_reads_colon_pairs():
    parsed = MODULE._parse_aliases("BTCUSDT:BTC-USD, ETHUSDT:ETH-USD,invalid")
    assert parsed == {"BTCUSDT": "BTC-USD", "ETHUSDT": "ETH-USD"}


def test_parser_accepts_halt_flags():
    parser = MODULE.build_parser()
    args = parser.parse_args(
        ["--halt-on-mismatch", "--cycles", "2", "--risk-profile", "professional"]
    )

    assert args.halt_on_mismatch is True
    assert args.cycles == 2
    assert args.risk_profile == "professional"
