"""FastAPI application scaffold for the PQTS API platform."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.responses import PlainTextResponse

from .auth import APIIdentity, build_token_store, require_admin, require_identity, require_operator
from .cache import APICache, get_cache
from .config import APISettings
from .correlation import RUN_HEADER, TRACE_HEADER, build_run_id, build_trace_id, with_correlation
from .persistence import APIPersistence
from .routes import core_router, sse_router, ws_router
from .state import APIRuntimeStore, StreamHub


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _render_prometheus_metrics(store: APIRuntimeStore) -> str:
    lines: list[str] = [
        "# HELP pqts_accounts_total Number of tracked accounts.",
        "# TYPE pqts_accounts_total gauge",
        f"pqts_accounts_total {len(store.accounts)}",
        "# HELP pqts_orders_total Total orders by account.",
        "# TYPE pqts_orders_total gauge",
    ]
    for account_id in sorted(store.accounts.keys()):
        orders = len(store.orders.get(account_id, []))
        fills = len(store.fills.get(account_id, []))
        incidents = len(store.risk_incidents.get(account_id, []))
        risk = store.risk_states.get(account_id)
        kill_switch = 1 if (risk and risk.kill_switch_active) else 0
        pnl_rows = store.pnl_snapshots.get(account_id, [])
        latest_net = float(pnl_rows[-1].net_pnl) if pnl_rows else 0.0
        lines.append(f'pqts_orders_total{{account_id="{account_id}"}} {orders}')
        lines.append(f'pqts_fills_total{{account_id="{account_id}"}} {fills}')
        lines.append(f'pqts_risk_incidents_total{{account_id="{account_id}"}} {incidents}')
        lines.append(f'pqts_kill_switch_active{{account_id="{account_id}"}} {kill_switch}')
        lines.append(f'pqts_net_pnl_usd{{account_id="{account_id}"}} {latest_net:.6f}')
    return "\n".join(lines) + "\n"


def create_app(settings: APISettings | None = None) -> FastAPI:
    """Create a configured FastAPI application."""
    resolved = settings or APISettings.from_env()
    openapi_url = "/openapi.json" if resolved.enable_openapi else None
    docs_url = "/docs" if resolved.enable_openapi else None
    redoc_url = "/redoc" if resolved.enable_openapi else None

    @asynccontextmanager
    async def lifespan(app_instance: FastAPI):  # type: ignore[no-untyped-def]
        app_instance.state.shutdown_in_progress = False
        yield
        app_instance.state.shutdown_in_progress = True

    app = FastAPI(
        title=resolved.service_name,
        version=resolved.service_version,
        openapi_url=openapi_url,
        docs_url=docs_url,
        redoc_url=redoc_url,
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def add_correlation_ids(request: Request, call_next):  # type: ignore[no-untyped-def]
        trace_id = request.headers.get(TRACE_HEADER, "").strip() or build_trace_id()
        run_id = request.headers.get(RUN_HEADER, "").strip() or build_run_id()
        request.state.trace_id = trace_id
        request.state.run_id = run_id
        response = await call_next(request)
        response.headers[TRACE_HEADER] = trace_id
        response.headers[RUN_HEADER] = run_id
        return response
    app.state.settings = resolved
    app.state.token_store = build_token_store(resolved.auth_tokens)
    app.state.cache = APICache.connect(resolved.redis_url)
    app.state.store = APIRuntimeStore.bootstrap()
    app.state.stream_hub = StreamHub()
    app.state.persistence = APIPersistence.connect(resolved.database_url)
    app.state.shutdown_in_progress = False
    if app.state.persistence is not None:
        try:
            app.state.persistence.initialize()
            app.state.persistence.seed_if_empty(app.state.store)
            app.state.persistence.hydrate_store(app.state.store)
        except Exception:  # noqa: BLE001
            # Keep API boot non-fatal when a configured DB is temporarily unavailable.
            app.state.persistence = None

    runtime_controls = {
        "deployment_profile": resolved.deployment_profile,
        "workers": resolved.workers,
        "limit_concurrency": resolved.limit_concurrency,
        "keepalive_timeout_seconds": resolved.keepalive_timeout_seconds,
        "graceful_shutdown_timeout_seconds": resolved.graceful_shutdown_timeout_seconds,
    }

    def _health_payload(request: Request) -> dict[str, Any]:
        return with_correlation(request, {
            "status": "ok",
            "service": resolved.service_name,
            "version": resolved.service_version,
            "environment": resolved.environment,
            "runtime_controls": runtime_controls,
            "timestamp": _utc_now_iso(),
        })

    def _ready_payload(request: Request) -> dict[str, Any]:
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
        return with_correlation(request, {
            "status": "ready" if not bool(app.state.shutdown_in_progress) else "draining",
            "service": resolved.service_name,
            "version": resolved.service_version,
            "environment": resolved.environment,
            "dependencies": dependencies,
            "runtime_controls": runtime_controls,
            "shutdown_in_progress": bool(app.state.shutdown_in_progress),
            "timestamp": _utc_now_iso(),
        })

    @app.get("/health", tags=["health"])
    def health(request: Request) -> dict[str, Any]:
        return _health_payload(request)

    @app.get("/healthz", tags=["health"])
    def healthz(request: Request) -> dict[str, Any]:
        return _health_payload(request)

    @app.get("/ready", tags=["health"])
    def ready(request: Request) -> dict[str, Any]:
        return _ready_payload(request)

    @app.get("/readyz", tags=["health"])
    def readyz(request: Request) -> dict[str, Any]:
        return _ready_payload(request)

    @app.get("/metrics", include_in_schema=False)
    def metrics(request: Request) -> PlainTextResponse:
        _ = request
        payload = _render_prometheus_metrics(app.state.store)
        return PlainTextResponse(content=payload, media_type="text/plain; version=0.0.4")

    @app.get("/v1/auth/me", tags=["auth"])
    def auth_me(
        request: Request,
        identity: Annotated[APIIdentity, Depends(require_identity)],
    ) -> dict[str, Any]:
        return with_correlation(request, {
            "identity": identity.to_dict(),
            "service": resolved.service_name,
            "timestamp": _utc_now_iso(),
        })

    @app.post("/v1/auth/sessions", tags=["auth"])
    def create_session(
        request: Request,
        identity: Annotated[APIIdentity, Depends(require_identity)],
        cache: Annotated[APICache, Depends(get_cache)],
    ) -> dict[str, Any]:
        session_token = f"sess_{uuid4().hex}"
        cache.set(f"session:{session_token}", identity.token, ttl_seconds=12 * 60 * 60)
        return with_correlation(request, {
            "session_token": session_token,
            "expires_in_seconds": 12 * 60 * 60,
            "identity": identity.to_dict(),
            "timestamp": _utc_now_iso(),
        })

    @app.post("/v1/operator/pause", tags=["operator"])
    def pause_trading(
        request: Request,
        identity: Annotated[APIIdentity, Depends(require_operator)],
    ) -> dict[str, Any]:
        return with_correlation(request, {
            "status": "accepted",
            "action": "pause_trading",
            "requested_by": identity.subject,
            "timestamp": _utc_now_iso(),
        })

    @app.post("/v1/admin/kill-switch", tags=["admin"])
    def admin_kill_switch(
        request: Request,
        identity: Annotated[APIIdentity, Depends(require_admin)],
    ) -> dict[str, Any]:
        return with_correlation(request, {
            "status": "accepted",
            "action": "kill_switch",
            "requested_by": identity.subject,
            "timestamp": _utc_now_iso(),
        })

    @app.post("/v1/stream/start", tags=["stream"])
    def start_stream_session(
        request: Request,
        identity: Annotated[APIIdentity, Depends(require_identity)],
    ) -> dict[str, Any]:
        return with_correlation(request, {
            "status": "accepted",
            "action": "start_stream_session",
            "requested_by": identity.subject,
            "channels": ["/ws/orders", "/ws/fills", "/ws/positions", "/ws/pnl", "/ws/risk"],
            "timestamp": _utc_now_iso(),
        })

    app.include_router(core_router)
    app.include_router(sse_router)
    app.include_router(ws_router)

    return app


app = create_app()
