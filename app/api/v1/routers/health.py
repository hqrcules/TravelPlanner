from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text

from app.api.v1.dependencies import DbSession
from app.core.config import Settings, get_settings
from app.utils.cache import get_cache

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    status: str
    db: str
    cache: str


@router.get("/health", response_model=HealthStatus, summary="Liveness & readiness probe")
async def health(
    session: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthStatus:
    db_status = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    cache_status = "ok"
    try:
        cache = get_cache()
        await cache.set("health:ping", "1", ttl=5)
        await cache.get("health:ping")
    except Exception:
        cache_status = "error" if settings.redis_url else "ok"

    overall = "ok" if db_status == "ok" and cache_status == "ok" else "degraded"
    return HealthStatus(status=overall, db=db_status, cache=cache_status)
