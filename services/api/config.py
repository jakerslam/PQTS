"""Runtime configuration for the PQTS API service."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class APISettings:
    service_name: str = "PQTS API"
    service_version: str = "0.1.0"
    environment: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8000
    enable_openapi: bool = True
    database_url: str = ""
    redis_url: str = ""
    auth_tokens: str = ""
    write_rate_limit_per_minute: int = 120
    read_rate_limit_per_minute: int = 600

    @classmethod
    def from_env(cls) -> "APISettings":
        return cls(
            service_name=os.getenv("PQTS_API_NAME", cls.service_name),
            service_version=os.getenv("PQTS_API_VERSION", cls.service_version),
            environment=os.getenv("PQTS_ENV", cls.environment),
            host=os.getenv("PQTS_API_HOST", cls.host),
            port=int(os.getenv("PQTS_API_PORT", str(cls.port))),
            enable_openapi=_env_bool("PQTS_API_ENABLE_OPENAPI", cls.enable_openapi),
            database_url=os.getenv("PQTS_DATABASE_URL", ""),
            redis_url=os.getenv("PQTS_REDIS_URL", ""),
            auth_tokens=os.getenv("PQTS_API_TOKENS", ""),
            write_rate_limit_per_minute=int(
                os.getenv("PQTS_API_WRITE_RPM", str(cls.write_rate_limit_per_minute))
            ),
            read_rate_limit_per_minute=int(
                os.getenv("PQTS_API_READ_RPM", str(cls.read_rate_limit_per_minute))
            ),
        )
