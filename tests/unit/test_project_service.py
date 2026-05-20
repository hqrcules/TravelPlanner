from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.db.models import Place, Project, ProjectStatus
from app.repositories.place import PlaceRepository
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectFilter, ProjectUpdate
from app.services.project_service import ProjectService


@pytest.fixture
def service(db_session: AsyncSession) -> ProjectService:
    return ProjectService(ProjectRepository(db_session), PlaceRepository(db_session))


@pytest.mark.asyncio
async def test_create_and_get(service: ProjectService) -> None:
    created = await service.create(
        ProjectCreate(name="Trip", description="d", start_date=date(2026, 6, 1))
    )
    fetched = await service.get(created.id)
    assert fetched.id == created.id
    assert fetched.status == ProjectStatus.PLANNING


@pytest.mark.asyncio
async def test_get_missing(service: ProjectService) -> None:
    import uuid

    with pytest.raises(NotFoundError):
        await service.get(uuid.uuid4())


@pytest.mark.asyncio
async def test_update_partial(service: ProjectService) -> None:
    project = await service.create(
        ProjectCreate(name="A", description=None, start_date=date(2026, 7, 1))
    )
    updated = await service.update(project.id, ProjectUpdate(name="B"))
    assert updated.name == "B"
    assert updated.start_date == date(2026, 7, 1)


@pytest.mark.asyncio
async def test_filter_by_status(service: ProjectService) -> None:
    await service.create(ProjectCreate(name="One", description=None, start_date=date(2026, 1, 1)))
    in_prog = await service.create(
        ProjectCreate(
            name="Two",
            description=None,
            start_date=date(2026, 2, 1),
            status=ProjectStatus.IN_PROGRESS,
        )
    )
    items, total = await service.list(ProjectFilter(status=ProjectStatus.IN_PROGRESS))
    assert total == 1
    assert items[0].id == in_prog.id


@pytest.mark.asyncio
async def test_delete_blocked_when_visited(
    service: ProjectService, db_session: AsyncSession
) -> None:
    project = await service.create(
        ProjectCreate(name="X", description=None, start_date=date(2026, 3, 1))
    )
    db_session.add(
        Place(
            project_id=project.id,
            external_id="42",
            title="t",
            visited=True,
        )
    )
    await db_session.flush()
    with pytest.raises(BusinessRuleError):
        await service.delete(project.id)


@pytest.mark.asyncio
async def test_delete_succeeds_when_no_visited(
    service: ProjectService, db_session: AsyncSession
) -> None:
    project = await service.create(
        ProjectCreate(name="Y", description=None, start_date=date(2026, 4, 1))
    )
    db_session.add(Place(project_id=project.id, external_id="1", title="t", visited=False))
    await db_session.flush()
    await service.delete(project.id)
    assert (await ProjectRepository(db_session).get(project.id)) is None


@pytest.mark.asyncio
async def test_sync_status_completed_when_all_visited(
    service: ProjectService, db_session: AsyncSession
) -> None:
    project = await service.create(
        ProjectCreate(name="Z", description=None, start_date=date(2026, 5, 1))
    )
    db_session.add_all(
        [
            Place(
                project_id=project.id,
                external_id=str(i),
                title="t",
                visited=True,
            )
            for i in range(3)
        ]
    )
    await db_session.flush()
    updated = await service.sync_status_from_places(project.id)
    assert updated.status == ProjectStatus.COMPLETED


@pytest.mark.asyncio
async def test_sync_status_back_to_in_progress(
    service: ProjectService, db_session: AsyncSession
) -> None:
    project = Project(
        name="W",
        description=None,
        start_date=date(2026, 6, 1),
        status=ProjectStatus.COMPLETED,
    )
    db_session.add(project)
    await db_session.flush()
    db_session.add_all(
        [
            Place(project_id=project.id, external_id="a", title="t", visited=True),
            Place(project_id=project.id, external_id="b", title="t", visited=False),
        ]
    )
    await db_session.flush()
    updated = await service.sync_status_from_places(project.id)
    assert updated.status == ProjectStatus.IN_PROGRESS
