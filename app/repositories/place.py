from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Place
from app.repositories.base import BaseRepository


class PlaceRepository(BaseRepository[Place]):
    model = Place

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    def list_query(self, project_id: uuid.UUID) -> Select[tuple[Place]]:
        return select(Place).where(Place.project_id == project_id).order_by(Place.created_at.asc())

    async def count_for_project(self, project_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Place).where(Place.project_id == project_id)
        return int((await self.session.execute(stmt)).scalar_one())

    async def get_by_external(self, project_id: uuid.UUID, external_id: str) -> Place | None:
        stmt = select(Place).where(
            Place.project_id == project_id,
            Place.external_id == external_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def all_visited(self, project_id: uuid.UUID) -> bool:
        total_stmt = select(func.count()).select_from(Place).where(Place.project_id == project_id)
        visited_stmt = (
            select(func.count())
            .select_from(Place)
            .where(Place.project_id == project_id, Place.visited.is_(True))
        )
        total = int((await self.session.execute(total_stmt)).scalar_one())
        visited = int((await self.session.execute(visited_stmt)).scalar_one())
        return total > 0 and total == visited
