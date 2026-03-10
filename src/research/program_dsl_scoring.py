"""Executable program DSL scoring with execution and symbolic-equivalence metrics."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

TOKEN_LITERAL = re.compile(r"^-?\d+(\.\d+)?$")
TOKEN_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COMMUTATIVE_OPS = {"ADD", "MUL", "MIN", "MAX"}


@dataclass(frozen=True)
class ProgramScore:
    execution_accuracy: float
    symbolic_equivalence: float
    parse_valid: bool
    candidate_value: float | None
    reference_value: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _split_args(payload: str) -> list[str]:
    args: list[str] = []
    depth = 0
    buf = []
    for char in payload:
        if char == "," and depth == 0:
            args.append("".join(buf).strip())
            buf = []
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("Mismatched parentheses in DSL program.")
        buf.append(char)
    final = "".join(buf).strip()
    if final:
        args.append(final)
    if depth != 0:
        raise ValueError("Mismatched parentheses in DSL program.")
    return args


def parse_program(program: str) -> Any:
    raw = str(program or "").strip()
    if not raw:
        raise ValueError("Program string is empty.")
    if TOKEN_LITERAL.match(raw):
        return ("LIT", float(raw))
    if TOKEN_IDENT.match(raw):
        return ("VAR", raw)

    open_idx = raw.find("(")
    close_idx = raw.rfind(")")
    if open_idx <= 0 or close_idx <= open_idx:
        raise ValueError(f"Invalid DSL program: {program}")
    op = raw[:open_idx].strip().upper()
    args_blob = raw[open_idx + 1 : close_idx]
    if not TOKEN_IDENT.match(op):
        raise ValueError(f"Invalid operator token: {op}")
    arg_tokens = _split_args(args_blob)
    if not arg_tokens:
        raise ValueError(f"Operator `{op}` requires arguments.")
    args = [parse_program(token) for token in arg_tokens]
    return ("CALL", op, tuple(args))


def _canonical(ast: Any) -> Any:
    kind = ast[0]
    if kind in {"LIT", "VAR"}:
        return ast
    _, op, args = ast
    canonical_args = tuple(_canonical(arg) for arg in args)
    if op in COMMUTATIVE_OPS:
        canonical_args = tuple(sorted(canonical_args, key=lambda item: repr(item)))
    return ("CALL", op, canonical_args)


def _eval(ast: Any, env: dict[str, float]) -> float:
    kind = ast[0]
    if kind == "LIT":
        return float(ast[1])
    if kind == "VAR":
        key = str(ast[1])
        if key not in env:
            raise ValueError(f"Variable `{key}` missing in evaluation env.")
        return float(env[key])

    _, op, args = ast
    values = [_eval(arg, env) for arg in args]
    if op == "ADD":
        return float(sum(values))
    if op == "SUB":
        if len(values) != 2:
            raise ValueError("SUB requires exactly 2 arguments.")
        return float(values[0] - values[1])
    if op == "MUL":
        out = 1.0
        for value in values:
            out *= value
        return float(out)
    if op == "DIV":
        if len(values) != 2:
            raise ValueError("DIV requires exactly 2 arguments.")
        denom = values[1]
        if abs(denom) < 1e-12:
            raise ValueError("DIV denominator is zero.")
        return float(values[0] / denom)
    if op == "MIN":
        return float(min(values))
    if op == "MAX":
        return float(max(values))
    if op == "ABS":
        if len(values) != 1:
            raise ValueError("ABS requires exactly 1 argument.")
        return float(abs(values[0]))
    raise ValueError(f"Unsupported operator `{op}`.")


def score_programs(
    *,
    candidate_program: str,
    reference_program: str,
    evaluation_env: dict[str, float],
    tolerance: float = 1e-6,
) -> ProgramScore:
    try:
        candidate_ast = parse_program(candidate_program)
        reference_ast = parse_program(reference_program)
    except ValueError:
        return ProgramScore(
            execution_accuracy=0.0,
            symbolic_equivalence=0.0,
            parse_valid=False,
            candidate_value=None,
            reference_value=None,
        )

    symbolic = 1.0 if _canonical(candidate_ast) == _canonical(reference_ast) else 0.0

    try:
        candidate_value = _eval(candidate_ast, evaluation_env)
        reference_value = _eval(reference_ast, evaluation_env)
    except ValueError:
        return ProgramScore(
            execution_accuracy=0.0,
            symbolic_equivalence=symbolic,
            parse_valid=False,
            candidate_value=None,
            reference_value=None,
        )

    delta = abs(candidate_value - reference_value)
    execution_accuracy = 1.0 if delta <= max(float(tolerance), 0.0) else 0.0
    if execution_accuracy == 0.0:
        execution_accuracy = max(0.0, 1.0 - min(delta / max(abs(reference_value), 1.0), 1.0))
    return ProgramScore(
        execution_accuracy=float(execution_accuracy),
        symbolic_equivalence=float(symbolic),
        parse_valid=True,
        candidate_value=float(candidate_value),
        reference_value=float(reference_value),
    )
