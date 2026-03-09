"""Shared FastAPI dependencies for runtime settings and request context."""

from __future__ import annotations

from fastapi import Request

from .config import APISettings


def get_settings(request: Request) -> APISettings:
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        return APISettings.from_env()
    return settings
