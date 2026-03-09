"""FastAPI application scaffold for the PQTS API platform."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Depends, FastAPI

from .auth import APIIdentity, build_token_store, require_admin, require_identity, require_operator
from .cache import APICache, get_cache
from .config import APISettings
from .persistence import APIPersistence
from .routes import core_router, ws_router
from .state import APIRuntimeStore, StreamHub


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
    app.state.token_store = build_token_store(resolved.auth_tokens)
    app.state.cache = APICache.connect(resolved.redis_url)
    app.state.store = APIRuntimeStore.bootstrap()
    app.state.stream_hub = StreamHub()
    app.state.persistence = APIPersistence.connect(resolved.database_url)
    if app.state.persistence is not None:
        app.state.persistence.initialize()
        app.state.persistence.seed_if_empty(app.state.store)
        app.state.persistence.hydrate_store(app.state.store)

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
        database_configured = bool(resolved.database_url)
        dependencies = {
            "database": {
                "configured": database_configured,
                "reachable": bool(app.state.persistence) if database_configured else None,
            },
            "redis": {
                "configured": bool(resolved.redis_url),
                "reachable": bool(app.state.cache.is_redis) if bool(resolved.redis_url) else None,
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

    @app.get("/v1/auth/me", tags=["auth"])
    def auth_me(identity: Annotated[APIIdentity, Depends(require_identity)]) -> dict[str, Any]:
        return {
            "identity": identity.to_dict(),
            "service": resolved.service_name,
            "timestamp": _utc_now_iso(),
        }

    @app.post("/v1/auth/sessions", tags=["auth"])
    def create_session(
        identity: Annotated[APIIdentity, Depends(require_identity)],
        cache: Annotated[APICache, Depends(get_cache)],
    ) -> dict[str, Any]:
        session_token = f"sess_{uuid4().hex}"
        cache.set(f"session:{session_token}", identity.token, ttl_seconds=12 * 60 * 60)
        return {
            "session_token": session_token,
            "expires_in_seconds": 12 * 60 * 60,
            "identity": identity.to_dict(),
            "timestamp": _utc_now_iso(),
        }

    @app.post("/v1/operator/pause", tags=["operator"])
    def pause_trading(identity: Annotated[APIIdentity, Depends(require_operator)]) -> dict[str, Any]:
        return {
            "status": "accepted",
            "action": "pause_trading",
            "requested_by": identity.subject,
            "timestamp": _utc_now_iso(),
        }

    @app.post("/v1/admin/kill-switch", tags=["admin"])
    def admin_kill_switch(identity: Annotated[APIIdentity, Depends(require_admin)]) -> dict[str, Any]:
        return {
            "status": "accepted",
            "action": "kill_switch",
            "requested_by": identity.subject,
            "timestamp": _utc_now_iso(),
        }

    app.include_router(core_router)
    app.include_router(ws_router)

    return app


app = create_app()
