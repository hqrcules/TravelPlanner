from __future__ import annotations

from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import Settings
from app.core.exceptions import UpstreamError, UpstreamNotFoundError


class ArticClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client or httpx.AsyncClient(
            base_url=settings.artic_base_url.rstrip("/"),
            timeout=settings.artic_timeout_seconds,
            headers={"Accept": "application/json", "User-Agent": "TravelPlanner/0.1"},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_artwork(self, external_id: str) -> dict[str, Any]:
        retrying = AsyncRetrying(
            reraise=True,
            stop=stop_after_attempt(self._settings.artic_retry_attempts),
            wait=wait_exponential(multiplier=0.2, max=2.0),
            retry=retry_if_exception_type((httpx.TransportError, _Retryable)),
        )
        try:
            async for attempt in retrying:
                with attempt:
                    return await self._fetch(external_id)
        except _Retryable as exc:
            raise UpstreamError(
                "Art Institute of Chicago API is unavailable.",
                details={"reason": str(exc)},
            ) from exc
        except httpx.TransportError as exc:
            raise UpstreamError(
                "Failed to reach Art Institute of Chicago API.",
                details={"reason": str(exc)},
            ) from exc
        raise UpstreamError("Failed to reach Art Institute of Chicago API.")

    async def _fetch(self, external_id: str) -> dict[str, Any]:
        try:
            response = await self._client.get(f"/artworks/{external_id}")
        except httpx.TimeoutException as exc:
            raise _Retryable("Upstream timeout") from exc

        if response.status_code == 404:
            raise UpstreamNotFoundError(f"Artwork '{external_id}' not found in Art Institute API.")
        if 500 <= response.status_code < 600:
            raise _Retryable(f"Upstream {response.status_code}")
        if response.status_code >= 400:
            raise UpstreamError(
                f"Art Institute API returned {response.status_code}.",
                details={"status": response.status_code},
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise UpstreamError("Invalid JSON from Art Institute API.") from exc

        data = payload.get("data")
        if not isinstance(data, dict):
            raise UpstreamError("Unexpected payload shape from Art Institute API.")
        return data


class _Retryable(Exception):
    pass
