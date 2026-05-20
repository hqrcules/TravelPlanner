from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.v1.dependencies import Pagination, get_project_service, pagination_params
from app.core.security import verify_basic_auth
from app.schemas.common import ErrorResponse, Page, PageMeta
from app.schemas.project import (
    ProjectCreate,
    ProjectFilter,
    ProjectRead,
    ProjectUpdate,
)
from app.services.project_service import ProjectService

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
    dependencies=[Depends(verify_basic_auth)],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required."},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)

ServiceDep = Annotated[ProjectService, Depends(get_project_service)]
FilterDep = Annotated[ProjectFilter, Depends()]
PageDep = Annotated[Pagination, Depends(pagination_params)]


@router.get(
    "",
    response_model=Page[ProjectRead],
    summary="List projects with filtering and pagination",
)
async def list_projects(
    service: ServiceDep,
    filters: FilterDep,
    page: PageDep,
) -> Page[ProjectRead]:
    items, total = await service.list(filters, limit=page.limit, offset=page.offset)
    return Page[ProjectRead](
        items=[ProjectRead.model_validate(item) for item in items],
        meta=PageMeta(total=total, limit=page.limit, offset=page.offset),
    )


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
async def create_project(payload: ProjectCreate, service: ServiceDep) -> ProjectRead:
    project = await service.create(payload)
    return ProjectRead.model_validate(project)


@router.get(
    "/{project_id}",
    response_model=ProjectRead,
    summary="Get project by id",
)
async def get_project(project_id: uuid.UUID, service: ServiceDep) -> ProjectRead:
    project = await service.get(project_id)
    return ProjectRead.model_validate(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectRead,
    summary="Update project fields",
)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    service: ServiceDep,
) -> ProjectRead:
    project = await service.update(project_id, payload)
    return ProjectRead.model_validate(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project (blocked if any place is visited)",
)
async def delete_project(project_id: uuid.UUID, service: ServiceDep) -> Response:
    await service.delete(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
