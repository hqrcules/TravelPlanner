from __future__ import annotations

import httpx
import pytest
import respx
from httpx import AsyncClient

from tests.conftest import artic_payload


@pytest.mark.asyncio
async def test_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/projects")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_credentials(client: AsyncClient) -> None:
    response = await client.get("/api/v1/projects", auth=("nope", "nope"))
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_and_list_project(client: AsyncClient, auth: tuple[str, str]) -> None:
    payload = {"name": "Berlin", "description": "trip", "start_date": "2026-06-01"}
    create = await client.post("/api/v1/projects", json=payload, auth=auth)
    assert create.status_code == 201, create.text
    project_id = create.json()["id"]

    listing = await client.get("/api/v1/projects", auth=auth)
    assert listing.status_code == 200
    body = listing.json()
    assert body["meta"]["total"] == 1
    assert body["items"][0]["id"] == project_id


@pytest.mark.asyncio
async def test_filter_projects_by_status(client: AsyncClient, auth: tuple[str, str]) -> None:
    await client.post(
        "/api/v1/projects",
        json={"name": "A", "start_date": "2026-01-01"},
        auth=auth,
    )
    await client.post(
        "/api/v1/projects",
        json={
            "name": "B",
            "start_date": "2026-02-01",
            "status": "in_progress",
        },
        auth=auth,
    )
    response = await client.get("/api/v1/projects?status=in_progress", auth=auth)
    body = response.json()
    assert body["meta"]["total"] == 1
    assert body["items"][0]["name"] == "B"


@pytest.mark.asyncio
async def test_get_404(client: AsyncClient, auth: tuple[str, str]) -> None:
    response = await client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000", auth=auth)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_blocked_with_visited(
    client: AsyncClient,
    auth: tuple[str, str],
    mock_artic: respx.Router,
) -> None:
    mock_artic.get("/artworks/5").mock(return_value=httpx.Response(200, json=artic_payload(5)))
    project = (
        await client.post(
            "/api/v1/projects",
            json={"name": "C", "start_date": "2026-03-01"},
            auth=auth,
        )
    ).json()
    place = (
        await client.post(
            f"/api/v1/projects/{project['id']}/places",
            json={"external_id": "5"},
            auth=auth,
        )
    ).json()
    await client.patch(
        f"/api/v1/projects/{project['id']}/places/{place['id']}",
        json={"visited": True},
        auth=auth,
    )

    response = await client.delete(f"/api/v1/projects/{project['id']}", auth=auth)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_delete_succeeds_without_visited(client: AsyncClient, auth: tuple[str, str]) -> None:
    project = (
        await client.post(
            "/api/v1/projects",
            json={"name": "D", "start_date": "2026-04-01"},
            auth=auth,
        )
    ).json()
    response = await client.delete(f"/api/v1/projects/{project['id']}", auth=auth)
    assert response.status_code == 204
