from __future__ import annotations

import uuid

from app.core.constants import DEFAULT_PAGE_LIMIT, MAX_PLACES_PER_PROJECT
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.db.models import Place
from app.repositories.place import PlaceRepository
from app.repositories.project import ProjectRepository
from app.schemas.place import PlaceCreate, PlaceUpdate
from app.services.artic_service import ArticService
from app.services.project_service import ProjectService


class PlaceService:
    def __init__(
        self,
        place_repo: PlaceRepository,
        project_repo: ProjectRepository,
        project_service: ProjectService,
        artic_service: ArticService,
    ) -> None:
        self._places = place_repo
        self._projects = project_repo
        self._project_service = project_service
        self._artic = artic_service

    async def _ensure_project(self, project_id: uuid.UUID) -> None:
        if await self._projects.get(project_id) is None:
            raise NotFoundError(f"Project {project_id} not found.")

    async def list(
        self,
        project_id: uuid.UUID,
        *,
        limit: int = DEFAULT_PAGE_LIMIT,
        offset: int = 0,
    ) -> tuple[list[Place], int]:
        await self._ensure_project(project_id)
        stmt = self._places.list_query(project_id)
        return await self._places.list_paginated(stmt, limit=limit, offset=offset)

    async def create(self, project_id: uuid.UUID, data: PlaceCreate) -> Place:
        await self._ensure_project(project_id)

        existing = await self._places.get_by_external(project_id, data.external_id)
        if existing is not None:
            raise ConflictError(
                "Place with this external_id already exists in this project.",
                details={"external_id": data.external_id},
            )

        count = await self._places.count_for_project(project_id)
        if count >= MAX_PLACES_PER_PROJECT:
            raise BusinessRuleError(
                f"Project already has the maximum of {MAX_PLACES_PER_PROJECT} places.",
            )

        artwork = await self._artic.get_artwork(data.external_id)
        title = ArticService.extract_title(artwork)

        place = Place(
            project_id=project_id,
            external_id=data.external_id,
            title=title,
            notes=data.notes,
            visited=False,
        )
        place = await self._places.add(place)
        await self._project_service.sync_status_from_places(project_id)
        return place

    async def get(self, project_id: uuid.UUID, place_id: uuid.UUID) -> Place:
        place = await self._places.get(place_id)
        if place is None or place.project_id != project_id:
            raise NotFoundError(f"Place {place_id} not found in project {project_id}.")
        return place

    async def update(
        self,
        project_id: uuid.UUID,
        place_id: uuid.UUID,
        data: PlaceUpdate,
    ) -> Place:
        place = await self.get(project_id, place_id)
        payload = data.model_dump(exclude_unset=True)
        if not payload:
            return place
        place = await self._places.update(place, payload)
        if "visited" in payload:
            await self._project_service.sync_status_from_places(project_id)
        return place

    async def delete(self, project_id: uuid.UUID, place_id: uuid.UUID) -> None:
        place = await self.get(project_id, place_id)
        await self._places.delete(place)
        await self._project_service.sync_status_from_places(project_id)
