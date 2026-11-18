"""Business rules and state transitions for human approval."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from geoops_api.approvals.interfaces import ApprovalConflictError, ApprovalRepository
from geoops_api.approvals.models import (
    ApprovalAction,
    ApprovalEvidence,
    ApprovalRequest,
)
from geoops_api.domain.models import ApprovalStatus, AssignmentStatus
from geoops_api.services.catalog import CatalogService
from geoops_api.services.dispatch import DispatchService, TicketNotDispatchableError

logger = logging.getLogger("geoops.approvals")


class ApprovalNotFoundError(LookupError):
    pass


class ApprovalValidationError(ValueError):
    pass


class ApprovalService:
    def __init__(
        self,
        *,
        repository: ApprovalRepository,
        catalog_service: CatalogService,
        dispatch_service: DispatchService,
        ttl: timedelta,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._catalog = catalog_service
        self._dispatch = dispatch_service
        self._ttl = ttl
        self._clock = clock or (lambda: datetime.now(UTC))

    async def request_assignment(
        self,
        *,
        ticket_id: str,
        technician_id: str,
        reason: str,
        requested_by: str,
    ) -> ApprovalRequest:
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise ApprovalValidationError("A reason is required")
        ticket = await self._catalog.get_ticket(ticket_id)
        if ticket is None:
            raise ApprovalNotFoundError(f"Ticket {ticket_id} was not found")
        technician = await self._catalog.get_technician(technician_id)
        if technician is None:
            raise ApprovalNotFoundError(f"Technician {technician_id} was not found")
        try:
            recommendation = await self._dispatch.recommend(ticket_id)
        except TicketNotDispatchableError as exc:
            raise ApprovalValidationError(str(exc)) from exc
        if recommendation is None:
            raise ApprovalNotFoundError(f"Ticket {ticket_id} was not found")
        candidate = next(
            (
                item
                for item in recommendation.eligible_candidates
                if item.technician_id == technician_id
            ),
            None,
        )
        if candidate is None:
            raise ApprovalValidationError(
                f"Technician {technician.name} is not eligible for ticket {ticket_id}"
            )

        current_assignment = next(
            (
                assignment
                for assignment in ticket.assignments
                if assignment.status in {AssignmentStatus.ACTIVE, AssignmentStatus.SCHEDULED}
            ),
            None,
        )
        if current_assignment and current_assignment.technician_id == technician_id:
            raise ApprovalValidationError(
                f"Technician {technician.name} is already assigned to ticket {ticket_id}"
            )

        active = await self.list(status=ApprovalStatus.PENDING)
        duplicate = next(
            (
                item
                for item in active
                if item.ticket_id == ticket_id and item.to_technician_id == technician_id
            ),
            None,
        )
        if duplicate:
            logger.info(
                "approval_proposal_reused",
                extra={
                    "approval_id": duplicate.approval_id,
                    "ticket_id": duplicate.ticket_id,
                    "approval_status": duplicate.status.value,
                },
            )
            return duplicate

        now = self._clock()
        approval = ApprovalRequest(
            approval_id=f"APR-{uuid4().hex[:12].upper()}",
            action=ApprovalAction.ASSIGN_TECHNICIAN,
            ticket_id=ticket_id,
            ticket_title=ticket.title,
            from_technician_id=(current_assignment.technician_id if current_assignment else None),
            from_technician_name=(
                current_assignment.technician_name if current_assignment else None
            ),
            to_technician_id=technician_id,
            to_technician_name=technician.name,
            reason=normalized_reason,
            status=ApprovalStatus.PENDING,
            requested_by=requested_by.strip(),
            requested_at=now,
            expires_at=now + self._ttl,
            evidence=ApprovalEvidence(
                policy_version=recommendation.policy_version,
                score=candidate.score or 0,
                distance_km=candidate.distance_km,
                travel_duration_minutes=candidate.travel_duration_minutes,
                route_provider=candidate.route_provider,
                route_is_estimate=candidate.route_is_estimate,
                matched_certification_ids=candidate.matched_certification_ids,
            ),
        )
        created = await self._repository.create(approval)
        logger.info(
            "approval_proposal_created",
            extra={
                "approval_id": created.approval_id,
                "ticket_id": created.ticket_id,
                "approval_status": created.status.value,
            },
        )
        return created

    async def get(self, approval_id: str) -> ApprovalRequest:
        record = await self._repository.get(approval_id)
        if record is None:
            raise ApprovalNotFoundError(f"Approval {approval_id} was not found")
        return await self._expire_if_needed(record)

    async def list(self, status: ApprovalStatus | None = None) -> list[ApprovalRequest]:
        records = await self._repository.list()
        refreshed = [await self._expire_if_needed(record) for record in records]
        if status is not None:
            refreshed = [record for record in refreshed if record.status == status]
        return refreshed

    async def decide(
        self,
        approval_id: str,
        *,
        decision: ApprovalStatus,
        decided_by: str,
        comment: str | None,
    ) -> ApprovalRequest:
        if decision not in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}:
            raise ApprovalValidationError("Decision must be approved or rejected")
        record = await self.get(approval_id)
        if record.status == decision:
            return record
        if record.status != ApprovalStatus.PENDING:
            raise ApprovalConflictError(f"Approval {approval_id} is already {record.status.value}")
        updated = record.model_copy(
            update={
                "status": decision,
                "decided_by": decided_by.strip(),
                "decided_at": self._clock(),
                "decision_comment": comment.strip() if comment else None,
                "version": record.version + 1,
            }
        )
        decided = await self._repository.transition(
            approval_id,
            expected_status=ApprovalStatus.PENDING,
            updated=updated,
        )
        logger.info(
            "approval_decided",
            extra={
                "approval_id": decided.approval_id,
                "ticket_id": decided.ticket_id,
                "approval_status": decided.status.value,
            },
        )
        return decided

    async def _expire_if_needed(self, record: ApprovalRequest) -> ApprovalRequest:
        if record.status != ApprovalStatus.PENDING or self._clock() < record.expires_at:
            return record
        expired = record.model_copy(
            update={
                "status": ApprovalStatus.EXPIRED,
                "version": record.version + 1,
            }
        )
        try:
            expired = await self._repository.transition(
                record.approval_id,
                expected_status=ApprovalStatus.PENDING,
                updated=expired,
            )
            logger.info(
                "approval_expired",
                extra={
                    "approval_id": expired.approval_id,
                    "ticket_id": expired.ticket_id,
                    "approval_status": expired.status.value,
                },
            )
            return expired
        except ApprovalConflictError as exc:
            latest = await self._repository.get(record.approval_id)
            if latest is None:
                raise ApprovalNotFoundError(f"Approval {record.approval_id} was not found") from exc
            return latest
