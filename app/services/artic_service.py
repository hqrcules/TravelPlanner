from __future__ import annotations

from typing import Any

from aiocache import BaseCache

from app.core.constants import ARTIC_CACHE_PREFIX
from app.integrations.artic_client import ArticClient


class ArticService:
    def __init__(self, client: ArticClient, cache: BaseCache, ttl_seconds: int) -> None:
        self._client = client
        self._cache = cache
        self._ttl = ttl_seconds

    async def get_artwork(self, external_id: str) -> dict[str, Any]:
        key = f"{ARTIC_CACHE_PREFIX}:{external_id}"
        cached = await self._cache.get(key)
        if cached is not None:
            return dict(cached)
        data = await self._client.get_artwork(external_id)
        await self._cache.set(key, data, ttl=self._ttl)
        return data

    @staticmethod
    def extract_title(artwork: dict[str, Any]) -> str:
        title = artwork.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()
        return f"Artwork {artwork.get('id', 'unknown')}"
