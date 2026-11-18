"""Idempotent dispatch consumer and recoverable outbox relay."""

import asyncio
import logging
from datetime import UTC, datetime

from geoops_api.approvals.interfaces import ApprovalConflictError
from geoops_api.domain.models import ApprovalStatus, Assignment, AssignmentStatus
from geoops_api.events import EventBus
from geoops_api.services.catalog import CatalogService
from geoops_api.services.dispatch import DispatchService, TicketNotDispatchableError
from geoops_api.workflow import DispatchEvent, WorkflowRepository

logger = logging.getLogger("geoops.worker")


class DispatchWorker:
    def __init__(
        self, repository: WorkflowRepository, catalog: CatalogService, dispatch: DispatchService
    ) -> None:
        self.repository = repository
        self.catalog = catalog
        self.dispatch = dispatch

    async def consume(self, event: DispatchEvent) -> None:
        if event.event_type != "dispatch.approved":
            raise ValueError("Unsupported event type")
        approval = await self.repository.get(event.approval_id)
        if approval is None or approval.ticket_id != event.ticket_id:
            raise ValueError("Event does not match an approval")
        if approval.status in {ApprovalStatus.EXECUTED, ApprovalStatus.FAILED}:
            return
        if approval.status != ApprovalStatus.APPROVED:
            raise ApprovalConflictError("An approved proposal is required")
        revision = await self.repository.revision()
        ticket = await self.catalog.get_ticket(approval.ticket_id)
        try:
            recommendation = await self.dispatch.recommend(approval.ticket_id)
        except TicketNotDispatchableError:
            recommendation = None
        eligible = recommendation and any(
            item.technician_id == approval.to_technician_id
            for item in recommendation.eligible_candidates
        )
        active = (
            [
                item.technician_id
                for item in ticket.assignments
                if item.status in {AssignmentStatus.ACTIVE, AssignmentStatus.SCHEDULED}
            ]
            if ticket
            else []
        )
        expected = [approval.from_technician_id] if approval.from_technician_id else []
        assignment = None
        if eligible and sorted(active) == sorted(expected) and recommendation:
            assignment = Assignment(
                assignment_id=f"ASG-{approval.approval_id}",
                ticket_id=approval.ticket_id,
                technician_id=approval.to_technician_id,
                scheduled_start=recommendation.service_window_start,
                scheduled_end=recommendation.service_window_end,
                status=AssignmentStatus.SCHEDULED,
                created_at=datetime.now(UTC),
            )
        await self.repository.finish(
            approval,
            revision=revision,
            assignment=assignment,
            error=None if assignment else "eligibility_or_assignment_changed",
        )
        logger.info(
            "dispatch_completed" if assignment else "dispatch_failed",
            extra={
                "approval_id": approval.approval_id,
                "event_id": event.event_id,
                "ticket_id": approval.ticket_id,
                "success": assignment is not None,
            },
        )


class OutboxRelay:
    def __init__(self, repository: WorkflowRepository, bus: EventBus) -> None:
        self.repository = repository
        self.bus = bus

    async def run_once(self) -> int:
        delivered = 0
        for event in await self.repository.events(unpublished_only=True):
            await self.bus.publish(event)
            await self.repository.published(event)
            delivered += 1
        return delivered

    async def run(self, interval: float) -> None:
        while True:
            try:
                await self.run_once()
            except Exception as exc:
                logger.error("outbox_delivery_failed", extra={"error_type": type(exc).__name__})
            await asyncio.sleep(interval)
