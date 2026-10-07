"""Read-only deterministic dispatch recommendation endpoints."""

from fastapi import APIRouter, HTTPException, Request, status

from geoops_api.container import ApplicationContainer
from geoops_api.schemas.dispatch import DispatchRecommendationResponse
from geoops_api.services.dispatch import TicketNotDispatchableError

router = APIRouter(prefix="/api/dispatch", tags=["dispatch"])


@router.get(
    "/recommendations/{ticket_id}",
    response_model=DispatchRecommendationResponse,
    summary="Rank eligible technicians for a ticket",
)
async def recommend_technicians(ticket_id: str, request: Request) -> DispatchRecommendationResponse:
    container: ApplicationContainer = request.app.state.container
    try:
        recommendation = await container.dispatch_service.recommend(ticket_id)
    except TicketNotDispatchableError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    if recommendation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} was not found",
        )
    return recommendation
