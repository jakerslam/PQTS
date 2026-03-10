"""Tests for executable DSL scoring metrics."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.program_dsl_scoring import score_programs


def test_score_programs_detects_symbolic_equivalence_for_commutative_ops() -> None:
    score = score_programs(
        candidate_program="ADD(B, A)",
        reference_program="ADD(A, B)",
        evaluation_env={"A": 2.0, "B": 3.0},
    )
    assert score.parse_valid is True
    assert score.symbolic_equivalence == 1.0
    assert score.execution_accuracy == 1.0


def test_score_programs_reports_non_equivalence() -> None:
    score = score_programs(
        candidate_program="SUB(A, B)",
        reference_program="ADD(A, B)",
        evaluation_env={"A": 5.0, "B": 2.0},
    )
    assert score.parse_valid is True
    assert score.symbolic_equivalence == 0.0
    assert score.execution_accuracy < 1.0


def test_score_programs_handles_parse_failures() -> None:
    score = score_programs(
        candidate_program="ADD(A,B",
        reference_program="ADD(A,B)",
        evaluation_env={"A": 1.0, "B": 2.0},
    )
    assert score.parse_valid is False
    assert score.execution_accuracy == 0.0
    assert score.symbolic_equivalence == 0.0
