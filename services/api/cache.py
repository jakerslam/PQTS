"""Cache/session/rate-limit primitives with Redis-first behavior."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, Request, status


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class APICache:
    redis_client: Any = None
    _memory_values: dict[str, str] = field(default_factory=dict)
    _memory_expiry: dict[str, datetime] = field(default_factory=dict)

    @classmethod
    def connect(cls, redis_url: str) -> "APICache":
        value = redis_url.strip()
        if not value:
            return cls(redis_client=None)
        try:
            import redis

            client = redis.Redis.from_url(value, decode_responses=True)
            client.ping()
            return cls(redis_client=client)
        except Exception:
            return cls(redis_client=None)

    @property
    def is_redis(self) -> bool:
        return self.redis_client is not None

    def _cleanup_key(self, key: str) -> None:
        expiry = self._memory_expiry.get(key)
        if expiry is None:
            return
        if _utc_now() >= expiry:
            self._memory_expiry.pop(key, None)
            self._memory_values.pop(key, None)

    def get(self, key: str) -> str | None:
        if self.redis_client is not None:
            value = self.redis_client.get(key)
            return str(value) if value is not None else None
        self._cleanup_key(key)
        return self._memory_values.get(key)

    def set(self, key: str, value: str, *, ttl_seconds: int | None = None) -> None:
        if self.redis_client is not None:
            if ttl_seconds is None:
                self.redis_client.set(key, value)
            else:
                self.redis_client.setex(key, ttl_seconds, value)
            return

        self._memory_values[key] = str(value)
        if ttl_seconds is None:
            self._memory_expiry.pop(key, None)
        else:
            self._memory_expiry[key] = _utc_now() + timedelta(seconds=max(int(ttl_seconds), 1))

    def incr(self, key: str, *, ttl_seconds: int) -> int:
        ttl = max(int(ttl_seconds), 1)
        if self.redis_client is not None:
            pipeline = self.redis_client.pipeline()
            pipeline.incr(key, 1)
            pipeline.expire(key, ttl, nx=True)
            value, _ = pipeline.execute()
            return int(value)

        self._cleanup_key(key)
        current = int(self._memory_values.get(key, "0")) + 1
        self._memory_values[key] = str(current)
        if key not in self._memory_expiry:
            self._memory_expiry[key] = _utc_now() + timedelta(seconds=ttl)
        return current


def get_cache(request: Request) -> APICache:
    cache = getattr(request.app.state, "cache", None)
    if isinstance(cache, APICache):
        return cache
    fallback = APICache.connect("")
    request.app.state.cache = fallback
    return fallback


def enforce_rate_limit(
    *,
    cache: APICache,
    bucket: str,
    limit: int,
    window_seconds: int,
) -> int:
    window = max(int(window_seconds), 1)
    max_allowed = max(int(limit), 1)
    key = f"rate_limit:{bucket}:{window}"
    current = cache.incr(key, ttl_seconds=window)
    if current > max_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for bucket `{bucket}`.",
        )
    return current
