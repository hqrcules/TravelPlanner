from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from aiocache import Cache
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MAX_PLACES_PER_PROJECT
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.db.models import Project
from app.repositories.place import PlaceRepository
from app.repositories.project import ProjectRepository
from app.schemas.place import PlaceCreate, PlaceUpdate
from app.services.artic_service import ArticService
from app.services.place_service import PlaceService
from app.services.project_service import ProjectService


class StubArticClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def get_artwork(self, external_id: str) -> dict[str, Any]:
        self.calls.append(external_id)
        return {"id": int(external_id), "title": f"Artwork {external_id}"}


def make_artic_service() -> tuple[ArticService, StubArticClient]:
    stub = StubArticClient()
    cache = Cache(Cache.MEMORY, namespace="test")
    service = ArticService(stub, cache, ttl_seconds=60)  # type: ignore[arg-type]
    return service, stub


@pytest.fixture
async def setup(db_session: AsyncSession) -> dict[str, Any]:
    artic, stub = make_artic_service()
    projects = ProjectRepository(db_session)
    places = PlaceRepository(db_session)
    project_service = ProjectService(projects, places)
    place_service = PlaceService(places, projects, project_service, artic)
    project = Project(name="P", description=None, start_date=date(2026, 1, 1))
    db_session.add(project)
    await db_session.flush()
    return {
        "place_service": place_service,
        "project": project,
        "stub": stub,
        "session": db_session,
    }


@pytest.mark.asyncio
async def test_create_place(setup: dict[str, Any]) -> None:
    service: PlaceService = setup["place_service"]
    place = await service.create(setup["project"].id, PlaceCreate(external_id="11"))
    assert place.title == "Artwork 11"
    assert place.visited is False


@pytest.mark.asyncio
async def test_create_place_unknown_project(setup: dict[str, Any]) -> None:
    import uuid

    service: PlaceService = setup["place_service"]
    with pytest.raises(NotFoundError):
        await service.create(uuid.uuid4(), PlaceCreate(external_id="11"))


@pytest.mark.asyncio
async def test_create_duplicate_external_id(setup: dict[str, Any]) -> None:
    service: PlaceService = setup["place_service"]
    await service.create(setup["project"].id, PlaceCreate(external_id="22"))
    with pytest.raises(ConflictError):
        await service.create(setup["project"].id, PlaceCreate(external_id="22"))


@pytest.mark.asyncio
async def test_create_enforces_max_limit(setup: dict[str, Any]) -> None:
    service: PlaceService = setup["place_service"]
    project_id = setup["project"].id
    for i in range(MAX_PLACES_PER_PROJECT):
        await service.create(project_id, PlaceCreate(external_id=str(i)))
    with pytest.raises(BusinessRuleError):
        await service.create(project_id, PlaceCreate(external_id="overflow"))


@pytest.mark.asyncio
async def test_update_visited_triggers_status_sync(setup: dict[str, Any]) -> None:
    service: PlaceService = setup["place_service"]
    project_id = setup["project"].id
    place = await service.create(project_id, PlaceCreate(external_id="9"))
    await service.update(project_id, place.id, PlaceUpdate(visited=True))
    session: AsyncSession = setup["session"]
    refreshed = await session.get(Project, project_id)
    assert refreshed is not None
    assert refreshed.status.value == "completed"


@pytest.mark.asyncio
async def test_delete_place(setup: dict[str, Any]) -> None:
    service: PlaceService = setup["place_service"]
    place = await service.create(setup["project"].id, PlaceCreate(external_id="3"))
    await service.delete(setup["project"].id, place.id)
    with pytest.raises(NotFoundError):
        await service.get(setup["project"].id, place.id)


@pytest.mark.asyncio
async def test_artic_service_caches_lookups(setup: dict[str, Any]) -> None:
    artic_service = setup["place_service"]._artic
    stub: StubArticClient = setup["stub"]
    await artic_service.get_artwork("200")
    await artic_service.get_artwork("200")
    assert stub.calls == ["200"]
