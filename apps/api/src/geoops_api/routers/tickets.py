"""Ticket browsing endpoints."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status

from geoops_api.container import ApplicationContainer
from geoops_api.domain.models import TicketPriority, TicketStatus
from geoops_api.schemas.catalog import TicketDetail, TicketListResponse

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


@router.get("", response_model=TicketListResponse, summary="List service tickets")
async def list_tickets(
    request: Request,
    ticket_status: Annotated[TicketStatus | None, Query(alias="status")] = None,
    priority: TicketPriority | None = None,
    query: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TicketListResponse:
    container: ApplicationContainer = request.app.state.container
    return await container.catalog_service.list_tickets(
        status=ticket_status,
        priority=priority,
        query=query,
        limit=limit,
        offset=offset,
    )


@router.get("/{ticket_id}", response_model=TicketDetail, summary="Get a service ticket")
async def get_ticket(ticket_id: str, request: Request) -> TicketDetail:
    container: ApplicationContainer = request.app.state.container
    ticket = await container.catalog_service.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} was not found",
        )
    return ticket
