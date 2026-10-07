"""Typed diagnostics for the configured maps provider."""

from fastapi import APIRouter, HTTPException, Request, status

from geoops_api.container import ApplicationContainer
from geoops_api.maps.models import (
    GeocodeNotFoundError,
    GeocodeResult,
    MapsProviderError,
    RouteMatrixResult,
    RouteResult,
)
from geoops_api.schemas.maps import GeocodeRequest, RouteMatrixRequest, RouteRequest

router = APIRouter(prefix="/api/maps", tags=["maps"])


@router.post("/geocode", response_model=GeocodeResult, summary="Geocode an address")
async def geocode(payload: GeocodeRequest, request: Request) -> GeocodeResult:
    container: ApplicationContainer = request.app.state.container
    try:
        return await container.maps_provider.geocode(payload.address)
    except GeocodeNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except MapsProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Maps provider could not geocode the address",
        ) from error


@router.post("/routes", response_model=RouteResult, summary="Compute a route")
async def compute_route(payload: RouteRequest, request: Request) -> RouteResult:
    container: ApplicationContainer = request.app.state.container
    departure_time = payload.departure_time or container.catalog_repository.dataset.reference_time
    try:
        return await container.maps_provider.compute_route(
            payload.origin,
            payload.destination,
            departure_time=departure_time,
        )
    except MapsProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Maps provider could not compute the route",
        ) from error


@router.post(
    "/route-matrix",
    response_model=RouteMatrixResult,
    summary="Compute a route matrix",
)
async def compute_route_matrix(payload: RouteMatrixRequest, request: Request) -> RouteMatrixResult:
    container: ApplicationContainer = request.app.state.container
    departure_time = payload.departure_time or container.catalog_repository.dataset.reference_time
    try:
        return await container.maps_provider.compute_route_matrix(
            payload.origins,
            payload.destinations,
            departure_time=departure_time,
        )
    except MapsProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Maps provider could not compute the route matrix",
        ) from error
