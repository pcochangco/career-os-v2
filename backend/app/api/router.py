from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.goals import router as goals_router
from app.api.routes.health import router as health_router
from app.api.routes.progress import router as progress_router
from app.api.routes.resources import router as resources_router
from app.api.routes.roadmaps import router as roadmaps_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(goals_router)
api_router.include_router(roadmaps_router)
api_router.include_router(progress_router)
api_router.include_router(resources_router)
