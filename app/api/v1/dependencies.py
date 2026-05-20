from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.constants import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from app.db.session import get_db
from app.integrations.artic_client import ArticClient
from app.repositories.place import PlaceRepository
from app.repositories.project import ProjectRepository
from app.services.artic_service import ArticService
from app.services.place_service import PlaceService
from app.services.project_service import ProjectService
from app.utils.cache import get_cache


@dataclass(slots=True)
class Pagination:
    limit: int
    offset: int


def pagination_params(
    limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(0, ge=0),
) -> Pagination:
    return Pagination(limit=limit, offset=offset)


DbSession = Annotated[AsyncSession, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_project_repository(session: DbSession) -> ProjectRepository:
    return ProjectRepository(session)


def get_place_repository(session: DbSession) -> PlaceRepository:
    return PlaceRepository(session)


def get_artic_service(settings: SettingsDep) -> ArticService:
    client = ArticClient(settings)
    return ArticService(client, get_cache(), settings.artic_cache_ttl_seconds)


def get_project_service(
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
    places: Annotated[PlaceRepository, Depends(get_place_repository)],
) -> ProjectService:
    return ProjectService(projects, places)


def get_place_service(
    places: Annotated[PlaceRepository, Depends(get_place_repository)],
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    artic: Annotated[ArticService, Depends(get_artic_service)],
) -> PlaceService:
    return PlaceService(places, projects, project_service, artic)
