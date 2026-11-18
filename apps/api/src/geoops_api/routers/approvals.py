"""Human approval proposal and decision endpoints."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status

from geoops_api.approvals.interfaces import ApprovalConflictError
from geoops_api.approvals.models import ApprovalRequest
from geoops_api.approvals.service import (
    ApprovalNotFoundError,
    ApprovalValidationError,
)
from geoops_api.container import ApplicationContainer
from geoops_api.domain.models import ApprovalStatus
from geoops_api.schemas.approvals import (
    ApprovalDecisionRequest,
    ApprovalListResponse,
    CreateApprovalRequest,
)

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("", response_model=ApprovalListResponse, summary="List approval requests")
async def list_approvals(
    request: Request,
    approval_status: Annotated[ApprovalStatus | None, Query(alias="status")] = None,
) -> ApprovalListResponse:
    container: ApplicationContainer = request.app.state.container
    items = await container.approval_service.list(status=approval_status)
    return ApprovalListResponse(items=items, total=len(items))


@router.post(
    "",
    response_model=ApprovalRequest,
    status_code=status.HTTP_201_CREATED,
    summary="Create a validated assignment proposal",
)
async def create_approval(payload: CreateApprovalRequest, request: Request) -> ApprovalRequest:
    container: ApplicationContainer = request.app.state.container
    try:
        return await container.approval_service.request_assignment(
            ticket_id=payload.ticket_id,
            technician_id=payload.technician_id,
            reason=payload.reason,
            requested_by=payload.requested_by,
        )
    except ApprovalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ApprovalValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/{approval_id}",
    response_model=ApprovalRequest,
    summary="Get an approval request",
)
async def get_approval(approval_id: str, request: Request) -> ApprovalRequest:
    container: ApplicationContainer = request.app.state.container
    try:
        return await container.approval_service.get(approval_id)
    except ApprovalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/{approval_id}/approve",
    response_model=ApprovalRequest,
    summary="Approve a pending proposal",
)
async def approve(
    approval_id: str, payload: ApprovalDecisionRequest, request: Request
) -> ApprovalRequest:
    return await _decide(
        approval_id,
        payload=payload,
        request=request,
        decision=ApprovalStatus.APPROVED,
    )


@router.post(
    "/{approval_id}/reject",
    response_model=ApprovalRequest,
    summary="Reject a pending proposal",
)
async def reject(
    approval_id: str, payload: ApprovalDecisionRequest, request: Request
) -> ApprovalRequest:
    return await _decide(
        approval_id,
        payload=payload,
        request=request,
        decision=ApprovalStatus.REJECTED,
    )


async def _decide(
    approval_id: str,
    *,
    payload: ApprovalDecisionRequest,
    request: Request,
    decision: ApprovalStatus,
) -> ApprovalRequest:
    container: ApplicationContainer = request.app.state.container
    try:
        return await container.approval_service.decide(
            approval_id,
            decision=decision,
            decided_by=payload.decided_by,
            comment=payload.comment,
        )
    except ApprovalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ApprovalConflictError, ApprovalValidationError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
