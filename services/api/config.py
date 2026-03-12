"""Runtime configuration for the PQTS API service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # Python 3.11+
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - fallback for local/dev runtimes
    import tomli as tomllib  # type: ignore[no-redef]


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _default_service_version() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    pyproject_path = repo_root / "pyproject.toml"
    if not pyproject_path.exists():
        return "0.1.0"
    try:
        payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except Exception:
        return "0.1.0"
    project = payload.get("project", {})
    if not isinstance(project, dict):
        return "0.1.0"
    version = str(project.get("version", "")).strip()
    return version or "0.1.0"


@dataclass(frozen=True)
class APISettings:
    service_name: str = "PQTS API"
    service_version: str = _default_service_version()
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
    billing_provider: str = "demo"
    plan_catalog_path: str = "config/monetization/plan_catalog.json"
    signup_trial_days: int = 14
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    stripe_price_enterprise: str = ""

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
            billing_provider=os.getenv("PQTS_BILLING_PROVIDER", cls.billing_provider),
            plan_catalog_path=os.getenv("PQTS_PLAN_CATALOG_PATH", cls.plan_catalog_path),
            signup_trial_days=max(
                int(os.getenv("PQTS_SIGNUP_TRIAL_DAYS", str(cls.signup_trial_days))),
                0,
            ),
            stripe_secret_key=os.getenv("PQTS_STRIPE_SECRET_KEY", ""),
            stripe_publishable_key=os.getenv("PQTS_STRIPE_PUBLISHABLE_KEY", ""),
            stripe_webhook_secret=os.getenv("PQTS_STRIPE_WEBHOOK_SECRET", ""),
            stripe_price_starter=os.getenv("PQTS_STRIPE_PRICE_STARTER", ""),
            stripe_price_pro=os.getenv("PQTS_STRIPE_PRICE_PRO", ""),
            stripe_price_enterprise=os.getenv("PQTS_STRIPE_PRICE_ENTERPRISE", ""),
        )
