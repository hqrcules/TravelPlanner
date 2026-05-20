from __future__ import annotations

from functools import lru_cache

from aiocache import BaseCache, Cache
from aiocache.serializers import JsonSerializer

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_cache() -> BaseCache:
    settings = get_settings()
    if settings.redis_url:
        from urllib.parse import urlparse

        parsed = urlparse(settings.redis_url)
        return Cache(
            Cache.REDIS,
            endpoint=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            db=int(parsed.path.lstrip("/") or "0"),
            password=parsed.password,
            serializer=JsonSerializer(),
            namespace="travel_planner",
        )
    return Cache(Cache.MEMORY, serializer=JsonSerializer(), namespace="travel_planner")


def reset_cache() -> None:
    get_cache.cache_clear()
