"""Tests for VaR/drawdown guardrails and new-risk gating decisions."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.persistence import EventPersistenceStore
from risk.var_drawdown_guardrails import VarDrawdownConfig, VarDrawdownGuardrail


def test_hard_breach_blocks_new_risk() -> None:
    guard = VarDrawdownGuardrail(
        config=VarDrawdownConfig(
            var95_limit_pct=0.02,
            var99_limit_pct=0.03,
            drawdown_soft_limit_pct=0.06,
            drawdown_hard_limit_pct=0.10,
        )
    )
    decision = guard.evaluate(
        capital=100_000.0,
        current_drawdown_pct=0.11,
        pnl_changes=[-2000.0] * 50,
        proposed_new_risk_delta_usd=1500.0,
        risk_budget_usd=4000.0,
    )
    assert decision.action == "block_new_risk"
    assert decision.allowed_new_risk is False
    assert decision.max_new_risk_delta_usd == 0.0


def test_hard_breach_allows_de_risking_flow() -> None:
    guard = VarDrawdownGuardrail()
    decision = guard.evaluate(
        capital=50_000.0,
        current_drawdown_pct=0.15,
        pnl_changes=[-1200.0, -1000.0, -800.0, -900.0],
        proposed_new_risk_delta_usd=-500.0,
        risk_budget_usd=2000.0,
    )
    assert decision.action == "block_new_risk"
    assert decision.allowed_new_risk is True
    assert "de-risking" in decision.reason


def test_soft_breach_reduces_risk_and_persists(tmp_path: Path) -> None:
    store = EventPersistenceStore(dsn=f"sqlite:///{tmp_path}/guardrails.db")
    guard = VarDrawdownGuardrail(
        config=VarDrawdownConfig(
            var95_limit_pct=0.01,
            var99_limit_pct=0.20,
            drawdown_soft_limit_pct=0.15,
            drawdown_hard_limit_pct=0.30,
            reduce_new_risk_multiplier=0.25,
        ),
        persistence_store=store,
    )
    decision = guard.evaluate(
        capital=100_000.0,
        current_drawdown_pct=0.05,
        pnl_changes=[-1800.0] * 50,
        proposed_new_risk_delta_usd=800.0,
        risk_budget_usd=4000.0,
    )
    assert decision.action == "reduce_new_risk"
    assert decision.allowed_new_risk is True
    assert decision.max_new_risk_delta_usd == 1000.0

    replayed = guard.replay_decisions()
    assert len(replayed) == 1
    assert replayed[0].action == "reduce_new_risk"
