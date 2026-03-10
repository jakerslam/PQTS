"""Executable entrypoint for the PQTS FastAPI service."""

from __future__ import annotations

from .app import app
from .config import APISettings

__all__ = ["app"]


def run() -> None:
    import uvicorn

    settings = APISettings.from_env()
    uvicorn.run(
        "services.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        workers=settings.workers,
        limit_concurrency=settings.limit_concurrency,
        timeout_keep_alive=settings.keepalive_timeout_seconds,
        timeout_graceful_shutdown=settings.graceful_shutdown_timeout_seconds,
    )


if __name__ == "__main__":
    run()
