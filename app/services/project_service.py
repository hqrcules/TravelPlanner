from __future__ import annotations

import uuid

from app.core.constants import DEFAULT_PAGE_LIMIT
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.db.models import Project, ProjectStatus
from app.repositories.place import PlaceRepository
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectFilter, ProjectUpdate


class ProjectService:
    def __init__(
        self,
        project_repo: ProjectRepository,
        place_repo: PlaceRepository,
    ) -> None:
        self._projects = project_repo
        self._places = place_repo

    async def create(self, data: ProjectCreate) -> Project:
        project = Project(
            name=data.name,
            description=data.description,
            start_date=data.start_date,
            status=data.status,
        )
        return await self._projects.add(project)

    async def get(self, project_id: uuid.UUID) -> Project:
        project = await self._projects.get(project_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found.")
        return project

    async def list(
        self,
        filters: ProjectFilter,
        *,
        limit: int = DEFAULT_PAGE_LIMIT,
        offset: int = 0,
    ) -> tuple[list[Project], int]:
        stmt = self._projects.build_query(filters)
        return await self._projects.list_paginated(stmt, limit=limit, offset=offset)

    async def update(self, project_id: uuid.UUID, data: ProjectUpdate) -> Project:
        project = await self.get(project_id)
        payload = data.model_dump(exclude_unset=True)
        if not payload:
            return project
        return await self._projects.update(project, payload)

    async def delete(self, project_id: uuid.UUID) -> None:
        project = await self.get(project_id)
        if await self._projects.has_visited_places(project_id):
            raise BusinessRuleError(
                "Cannot delete project with visited places.",
                details={"project_id": str(project_id)},
            )
        await self._projects.delete(project)

    async def sync_status_from_places(self, project_id: uuid.UUID) -> Project:
        project = await self.get(project_id)
        place_count = await self._places.count_for_project(project_id)
        if place_count == 0:
            if project.status == ProjectStatus.COMPLETED:
                project = await self._projects.update(project, {"status": ProjectStatus.PLANNING})
            return project
        all_visited = await self._places.all_visited(project_id)
        if all_visited and project.status != ProjectStatus.COMPLETED:
            return await self._projects.update(project, {"status": ProjectStatus.COMPLETED})
        if not all_visited and project.status == ProjectStatus.COMPLETED:
            return await self._projects.update(project, {"status": ProjectStatus.IN_PROGRESS})
        return project
