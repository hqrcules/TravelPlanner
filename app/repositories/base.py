from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, entity_id: uuid.UUID) -> ModelT | None:
        return await self.session.get(self.model, entity_id)

    async def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def update(self, entity: ModelT, data: dict[str, Any]) -> ModelT:
        for key, value in data.items():
            setattr(entity, key, value)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def list_paginated(
        self,
        stmt: Select[tuple[ModelT]],
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[ModelT], int]:
        total_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = (await self.session.execute(total_stmt)).scalar_one()
        paginated = stmt.limit(limit).offset(offset)
        items = list((await self.session.execute(paginated)).scalars().all())
        return items, int(total)
