"""FastAPI application factory and ASGI entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from geoops_api.config import Settings, get_settings
from geoops_api.logging import configure_logging
from geoops_api.middleware import RequestTelemetryMiddleware
from geoops_api.routers.health import router as health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construct the API with explicit, testable dependencies."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    application = FastAPI(
        title="GeoOps AI API",
        summary="Operations gateway for the GeoOps AI platform.",
        version=resolved_settings.version,
    )
    application.state.settings = resolved_settings

    application.add_middleware(RequestTelemetryMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health_router)
    return application


app = create_app()
