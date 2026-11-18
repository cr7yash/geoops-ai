"""Current operational counts derived from persisted records."""

from fastapi import APIRouter, Request

from geoops_api.container import ApplicationContainer
from geoops_api.domain.models import ApprovalStatus, AssignmentStatus

router = APIRouter(prefix="/api", tags=["operations"])


@router.get("/operations")
async def summary(request: Request) -> dict[str, object]:
    container: ApplicationContainer = request.app.state.container
    await container.catalog_repository.refresh()
    dataset = container.catalog_repository.dataset
    tickets = await container.catalog_service.list_tickets(
        status=None, priority=None, query=None, limit=100, offset=0
    )
    active = [ticket for ticket in tickets.items if ticket.status not in {"completed", "cancelled"}]
    approvals = await container.approval_service.list()
    runs = await container.approval_repository.store.scan("agent_runs")
    return {
        "active_tickets": len(active),
        "sla_at_risk": sum(ticket.sla_state in {"at_risk", "overdue"} for ticket in active),
        "available_technicians": sum(item.status == "available" for item in dataset.technicians),
        "pending_approvals": sum(item.status == ApprovalStatus.PENDING for item in approvals),
        "completed_dispatches": sum(item.status == ApprovalStatus.EXECUTED for item in approvals),
        "reference_time": dataset.reference_time,
        "recent_agent_runs": sorted(runs, key=lambda row: row["started_at"], reverse=True)[:5],
    }


@router.get("/assignments")
async def assignments(request: Request) -> dict[str, object]:
    container: ApplicationContainer = request.app.state.container
    await container.catalog_repository.refresh()
    items = [
        item.model_dump(mode="json")
        for item in container.catalog_repository.dataset.assignments
        if item.status in {AssignmentStatus.ACTIVE, AssignmentStatus.SCHEDULED}
    ]
    return {"items": items, "total": len(items)}
