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
    deployment_profile: str = "dev"
    workers: int = 1
    limit_concurrency: int = 256
    keepalive_timeout_seconds: int = 5
    graceful_shutdown_timeout_seconds: int = 30

    @staticmethod
    def _profile_defaults(profile: str) -> dict[str, int]:
        token = str(profile or "dev").strip().lower()
        defaults = {
            "dev": {
                "workers": 1,
                "limit_concurrency": 256,
                "keepalive_timeout_seconds": 5,
                "graceful_shutdown_timeout_seconds": 30,
            },
            "canary": {
                "workers": 2,
                "limit_concurrency": 384,
                "keepalive_timeout_seconds": 8,
                "graceful_shutdown_timeout_seconds": 45,
            },
            "production": {
                "workers": 4,
                "limit_concurrency": 1024,
                "keepalive_timeout_seconds": 10,
                "graceful_shutdown_timeout_seconds": 60,
            },
        }
        return defaults.get(token, defaults["dev"])

    @classmethod
    def from_env(cls) -> "APISettings":
        profile = os.getenv("PQTS_API_DEPLOYMENT_PROFILE", cls.deployment_profile).strip().lower()
        profile_defaults = cls._profile_defaults(profile)
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
            deployment_profile=profile,
            workers=max(int(os.getenv("PQTS_API_WORKERS", str(profile_defaults["workers"]))), 1),
            limit_concurrency=max(
                int(
                    os.getenv(
                        "PQTS_API_LIMIT_CONCURRENCY",
                        str(profile_defaults["limit_concurrency"]),
                    )
                ),
                1,
            ),
            keepalive_timeout_seconds=max(
                int(
                    os.getenv(
                        "PQTS_API_KEEPALIVE_TIMEOUT_SECONDS",
                        str(profile_defaults["keepalive_timeout_seconds"]),
                    )
                ),
                1,
            ),
            graceful_shutdown_timeout_seconds=max(
                int(
                    os.getenv(
                        "PQTS_API_GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS",
                        str(profile_defaults["graceful_shutdown_timeout_seconds"]),
                    )
                ),
                1,
            ),
        )
