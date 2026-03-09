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
    )


if __name__ == "__main__":
    run()
