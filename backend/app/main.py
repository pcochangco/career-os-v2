from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.ai.providers.base import RoadmapProviderError
from app.ai.service import RoadmapQualityError
from app.api.router import api_router
from app.core.config import get_settings
from app.web import mount_frontend


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(RoadmapProviderError)
    async def handle_provider_error(
        request: Request,
        error: RoadmapProviderError,
    ) -> JSONResponse:
        del request, error
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Roadmap generation is temporarily unavailable. Please try again."},
        )

    @application.exception_handler(RoadmapQualityError)
    async def handle_quality_error(
        request: Request,
        error: RoadmapQualityError,
    ) -> JSONResponse:
        del request, error
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": "CareerOS could not produce a trustworthy roadmap yet. Please try again."
            },
        )

    application.include_router(api_router, prefix="/api/v1")
    mount_frontend(application, settings.static_directory)
    return application


app = create_app()
