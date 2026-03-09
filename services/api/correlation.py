"""Correlation ID utilities for request/stream tracing."""

from __future__ import annotations

from uuid import uuid4

from fastapi import Request

TRACE_HEADER = "X-Trace-Id"
RUN_HEADER = "X-Run-Id"


def build_trace_id() -> str:
    return f"trace-{uuid4().hex}"


def build_run_id() -> str:
    return f"run-{uuid4().hex}"


def read_request_correlation(request: Request) -> tuple[str, str]:
    trace_id = getattr(request.state, "trace_id", "") or build_trace_id()
    run_id = getattr(request.state, "run_id", "") or build_run_id()
    return str(trace_id), str(run_id)


def with_correlation(request: Request, payload: dict) -> dict:
    trace_id, run_id = read_request_correlation(request)
    enriched = dict(payload)
    enriched["trace_id"] = trace_id
    enriched["run_id"] = run_id
    return enriched
