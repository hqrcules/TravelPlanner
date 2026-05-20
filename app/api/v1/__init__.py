from fastapi import APIRouter

from app.api.v1.routers import places, projects

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(projects.router)
api_router.include_router(places.router)
