"""FastAPI application scaffold for the PQTS API platform."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI

from .config import APISettings


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_app(settings: APISettings | None = None) -> FastAPI:
    """Create a configured FastAPI application."""
    resolved = settings or APISettings.from_env()
    openapi_url = "/openapi.json" if resolved.enable_openapi else None
    docs_url = "/docs" if resolved.enable_openapi else None
    redoc_url = "/redoc" if resolved.enable_openapi else None

    app = FastAPI(
        title=resolved.service_name,
        version=resolved.service_version,
        openapi_url=openapi_url,
        docs_url=docs_url,
        redoc_url=redoc_url,
    )
    app.state.settings = resolved

    @app.get("/health", tags=["health"])
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": resolved.service_name,
            "version": resolved.service_version,
            "environment": resolved.environment,
            "timestamp": _utc_now_iso(),
        }

    @app.get("/ready", tags=["health"])
    def ready() -> dict[str, Any]:
        dependencies = {
            "database": {
                "configured": bool(resolved.database_url),
                "reachable": None,
            },
            "redis": {
                "configured": bool(resolved.redis_url),
                "reachable": None,
            },
        }
        return {
            "status": "ready",
            "service": resolved.service_name,
            "version": resolved.service_version,
            "environment": resolved.environment,
            "dependencies": dependencies,
            "timestamp": _utc_now_iso(),
        }

    return app


app = create_app()
