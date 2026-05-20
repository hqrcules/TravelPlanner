from __future__ import annotations

import uuid

from sqlalchemy import Select, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Place, Project
from app.repositories.base import BaseRepository
from app.schemas.project import ProjectFilter


class ProjectRepository(BaseRepository[Project]):
    model = Project

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    def build_query(self, filters: ProjectFilter) -> Select[tuple[Project]]:
        stmt = select(Project).order_by(Project.created_at.desc())
        if filters.status is not None:
            stmt = stmt.where(Project.status == filters.status)
        if filters.start_date_from is not None:
            stmt = stmt.where(Project.start_date >= filters.start_date_from)
        if filters.start_date_to is not None:
            stmt = stmt.where(Project.start_date <= filters.start_date_to)
        if filters.search:
            pattern = f"%{filters.search.lower()}%"
            stmt = stmt.where(Project.name.ilike(pattern))
        return stmt

    async def has_visited_places(self, project_id: uuid.UUID) -> bool:
        stmt = select(exists().where(Place.project_id == project_id, Place.visited.is_(True)))
        result = await self.session.execute(stmt)
        return bool(result.scalar())
