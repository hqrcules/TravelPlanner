from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlaceBase(BaseModel):
    external_id: str = Field(min_length=1, max_length=64)
    notes: str | None = Field(default=None, max_length=5000)


class PlaceCreate(PlaceBase):
    pass


class PlaceUpdate(BaseModel):
    visited: bool | None = None
    notes: str | None = Field(default=None, max_length=5000)


class PlaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    external_id: str
    title: str
    visited: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime
