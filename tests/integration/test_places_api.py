from __future__ import annotations

import httpx
import pytest
import respx
from httpx import AsyncClient

from tests.conftest import artic_payload


async def _create_project(client: AsyncClient, auth: tuple[str, str]) -> str:
    response = await client.post(
        "/api/v1/projects",
        json={"name": "Trip", "start_date": "2026-06-01"},
        auth=auth,
    )
    assert response.status_code == 201
    return str(response.json()["id"])


@pytest.mark.asyncio
async def test_add_place_with_artic_verification(
    client: AsyncClient,
    auth: tuple[str, str],
    mock_artic: respx.Router,
) -> None:
    mock_artic.get("/artworks/27992").mock(
        return_value=httpx.Response(200, json=artic_payload(27992, "Nighthawks"))
    )
    project_id = await _create_project(client, auth)
    response = await client.post(
        f"/api/v1/projects/{project_id}/places",
        json={"external_id": "27992"},
        auth=auth,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "Nighthawks"
    assert body["visited"] is False


@pytest.mark.asyncio
async def test_duplicate_external_id_conflict(
    client: AsyncClient,
    auth: tuple[str, str],
    mock_artic: respx.Router,
) -> None:
    mock_artic.get("/artworks/1").mock(return_value=httpx.Response(200, json=artic_payload(1)))
    project_id = await _create_project(client, auth)
    await client.post(
        f"/api/v1/projects/{project_id}/places",
        json={"external_id": "1"},
        auth=auth,
    )
    response = await client.post(
        f"/api/v1/projects/{project_id}/places",
        json={"external_id": "1"},
        auth=auth,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_external_artwork_not_found_returns_422(
    client: AsyncClient,
    auth: tuple[str, str],
    mock_artic: respx.Router,
) -> None:
    mock_artic.get("/artworks/404404").mock(return_value=httpx.Response(404))
    project_id = await _create_project(client, auth)
    response = await client.post(
        f"/api/v1/projects/{project_id}/places",
        json={"external_id": "404404"},
        auth=auth,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_artic_upstream_error_returns_502(
    client: AsyncClient,
    auth: tuple[str, str],
    mock_artic: respx.Router,
) -> None:
    mock_artic.get("/artworks/500500").mock(return_value=httpx.Response(503))
    project_id = await _create_project(client, auth)
    response = await client.post(
        f"/api/v1/projects/{project_id}/places",
        json={"external_id": "500500"},
        auth=auth,
    )
    assert response.status_code == 502


@pytest.mark.asyncio
async def test_max_places_limit(
    client: AsyncClient,
    auth: tuple[str, str],
    mock_artic: respx.Router,
) -> None:
    for i in range(10):
        mock_artic.get(f"/artworks/{i}").mock(
            return_value=httpx.Response(200, json=artic_payload(i))
        )
    mock_artic.get("/artworks/overflow").mock(
        return_value=httpx.Response(200, json=artic_payload("overflow"))
    )
    project_id = await _create_project(client, auth)
    for i in range(10):
        ok = await client.post(
            f"/api/v1/projects/{project_id}/places",
            json={"external_id": str(i)},
            auth=auth,
        )
        assert ok.status_code == 201
    response = await client.post(
        f"/api/v1/projects/{project_id}/places",
        json={"external_id": "overflow"},
        auth=auth,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_auto_complete_status(
    client: AsyncClient,
    auth: tuple[str, str],
    mock_artic: respx.Router,
) -> None:
    mock_artic.get("/artworks/a").mock(return_value=httpx.Response(200, json=artic_payload("a")))
    mock_artic.get("/artworks/b").mock(return_value=httpx.Response(200, json=artic_payload("b")))
    project_id = await _create_project(client, auth)
    place_a = (
        await client.post(
            f"/api/v1/projects/{project_id}/places",
            json={"external_id": "a"},
            auth=auth,
        )
    ).json()
    place_b = (
        await client.post(
            f"/api/v1/projects/{project_id}/places",
            json={"external_id": "b"},
            auth=auth,
        )
    ).json()
    await client.patch(
        f"/api/v1/projects/{project_id}/places/{place_a['id']}",
        json={"visited": True},
        auth=auth,
    )
    await client.patch(
        f"/api/v1/projects/{project_id}/places/{place_b['id']}",
        json={"visited": True},
        auth=auth,
    )
    project = (await client.get(f"/api/v1/projects/{project_id}", auth=auth)).json()
    assert project["status"] == "completed"

    await client.patch(
        f"/api/v1/projects/{project_id}/places/{place_a['id']}",
        json={"visited": False},
        auth=auth,
    )
    project = (await client.get(f"/api/v1/projects/{project_id}", auth=auth)).json()
    assert project["status"] == "in_progress"
