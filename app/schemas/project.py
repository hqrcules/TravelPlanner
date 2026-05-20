from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.project import ProjectStatus


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    start_date: date


class ProjectCreate(ProjectBase):
    status: ProjectStatus = ProjectStatus.PLANNING


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    start_date: date | None = None
    status: ProjectStatus | None = None


class ProjectRead(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


class ProjectFilter(BaseModel):
    status: ProjectStatus | None = None
    start_date_from: date | None = None
    start_date_to: date | None = None
    search: str | None = Field(default=None, min_length=1, max_length=200)
