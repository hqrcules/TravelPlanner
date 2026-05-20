from __future__ import annotations

import httpx
import pytest
import respx

from app.core.config import get_settings
from app.core.exceptions import UpstreamError, UpstreamNotFoundError
from app.integrations.artic_client import ArticClient
from tests.conftest import artic_payload


@pytest.mark.asyncio
async def test_get_artwork_success(mock_artic: respx.Router) -> None:
    mock_artic.get("/artworks/123").mock(
        return_value=httpx.Response(200, json=artic_payload(123, "Mona"))
    )
    client = ArticClient(get_settings())
    try:
        data = await client.get_artwork("123")
    finally:
        await client.aclose()
    assert data["id"] == 123
    assert data["title"] == "Mona"


@pytest.mark.asyncio
async def test_get_artwork_not_found(mock_artic: respx.Router) -> None:
    mock_artic.get("/artworks/999").mock(return_value=httpx.Response(404))
    client = ArticClient(get_settings())
    try:
        with pytest.raises(UpstreamNotFoundError):
            await client.get_artwork("999")
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_get_artwork_retries_on_5xx(mock_artic: respx.Router) -> None:
    route = mock_artic.get("/artworks/77").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(503),
            httpx.Response(200, json=artic_payload(77, "Third")),
        ]
    )
    client = ArticClient(get_settings())
    try:
        data = await client.get_artwork("77")
    finally:
        await client.aclose()
    assert route.call_count == 3
    assert data["title"] == "Third"


@pytest.mark.asyncio
async def test_get_artwork_upstream_4xx_no_retry(mock_artic: respx.Router) -> None:
    route = mock_artic.get("/artworks/55").mock(return_value=httpx.Response(418))
    client = ArticClient(get_settings())
    try:
        with pytest.raises(UpstreamError):
            await client.get_artwork("55")
    finally:
        await client.aclose()
    assert route.call_count == 1
