"""Technician browsing endpoints."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status

from geoops_api.container import ApplicationContainer
from geoops_api.domain.models import TechnicianStatus
from geoops_api.schemas.catalog import TechnicianDetail, TechnicianListResponse

router = APIRouter(prefix="/api/technicians", tags=["technicians"])


@router.get("", response_model=TechnicianListResponse, summary="List technicians")
async def list_technicians(
    request: Request,
    technician_status: Annotated[TechnicianStatus | None, Query(alias="status")] = None,
    certification_id: str | None = None,
    query: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TechnicianListResponse:
    container: ApplicationContainer = request.app.state.container
    return await container.catalog_service.list_technicians(
        status=technician_status,
        certification_id=certification_id,
        query=query,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{technician_id}",
    response_model=TechnicianDetail,
    summary="Get a technician",
)
async def get_technician(technician_id: str, request: Request) -> TechnicianDetail:
    container: ApplicationContainer = request.app.state.container
    technician = await container.catalog_service.get_technician(technician_id)
    if technician is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Technician {technician_id} was not found",
        )
    return technician
