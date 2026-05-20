from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.v1.dependencies import Pagination, get_place_service, pagination_params
from app.core.security import verify_basic_auth
from app.schemas.common import ErrorResponse, Page, PageMeta
from app.schemas.place import PlaceCreate, PlaceRead, PlaceUpdate
from app.services.place_service import PlaceService

router = APIRouter(
    prefix="/projects/{project_id}/places",
    tags=["places"],
    dependencies=[Depends(verify_basic_auth)],
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)

ServiceDep = Annotated[PlaceService, Depends(get_place_service)]
PageDep = Annotated[Pagination, Depends(pagination_params)]


@router.get(
    "",
    response_model=Page[PlaceRead],
    summary="List places of a project",
)
async def list_places(
    project_id: uuid.UUID,
    service: ServiceDep,
    page: PageDep,
) -> Page[PlaceRead]:
    items, total = await service.list(project_id, limit=page.limit, offset=page.offset)
    return Page[PlaceRead](
        items=[PlaceRead.model_validate(item) for item in items],
        meta=PageMeta(total=total, limit=page.limit, offset=page.offset),
    )


@router.post(
    "",
    response_model=PlaceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a place to a project (verified via Art Institute API)",
)
async def create_place(
    project_id: uuid.UUID,
    payload: PlaceCreate,
    service: ServiceDep,
) -> PlaceRead:
    place = await service.create(project_id, payload)
    return PlaceRead.model_validate(place)


@router.patch(
    "/{place_id}",
    response_model=PlaceRead,
    summary="Update a place (notes / visited flag)",
)
async def update_place(
    project_id: uuid.UUID,
    place_id: uuid.UUID,
    payload: PlaceUpdate,
    service: ServiceDep,
) -> PlaceRead:
    place = await service.update(project_id, place_id, payload)
    return PlaceRead.model_validate(place)


@router.delete(
    "/{place_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a place from a project",
)
async def delete_place(
    project_id: uuid.UUID,
    place_id: uuid.UUID,
    service: ServiceDep,
) -> Response:
    await service.delete(project_id, place_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
