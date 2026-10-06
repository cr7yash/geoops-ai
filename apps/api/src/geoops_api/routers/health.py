"""Service health route."""

from fastapi import APIRouter, Request

from geoops_api.config import Settings
from geoops_api.schemas.health import HealthResponse

router = APIRouter(tags=["system"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Report API health",
    description="Returns deterministic service metadata when the API process is healthy.",
)
async def health(request: Request) -> HealthResponse:
    settings: Settings = request.app.state.settings
    return HealthResponse(
        service=settings.service_name,
        environment=settings.app_env,
        version=settings.version,
    )
