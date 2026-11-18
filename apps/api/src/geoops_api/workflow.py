"""Atomic approval, outbox, and assignment operations shared by all transports."""

from __future__ import annotations

import builtins
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from geoops_api.approvals.interfaces import ApprovalConflictError
from geoops_api.approvals.models import ApprovalRequest
from geoops_api.domain.models import ApprovalStatus, Assignment
from geoops_api.state import DocumentStore


class DispatchEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str
    event_type: str = "dispatch.approved"
    approval_id: str
    ticket_id: str
    occurred_at: datetime
    published: bool = False
    attempts: int = Field(default=0, ge=0)
    error_type: str | None = None
    next_attempt_at: datetime | None = None


class WorkflowRepository:
    def __init__(self, store: DocumentStore) -> None:
        self.store = store

    async def create(self, approval: ApprovalRequest) -> ApprovalRequest:
        key = f"approvals/{approval.approval_id}"

        def create(documents: dict[str, Any]) -> dict[str, Any]:
            if documents[key]:
                raise ApprovalConflictError("Approval already exists")
            return {key: approval.model_dump(mode="json")}

        await self.store.transact([key], create)
        return approval

    async def get(self, approval_id: str) -> ApprovalRequest | None:
        document = await self.store.get(f"approvals/{approval_id}")
        return ApprovalRequest.model_validate(document) if document else None

    async def list(self, status: ApprovalStatus | None = None) -> list[ApprovalRequest]:
        records = [
            ApprovalRequest.model_validate(item) for item in await self.store.scan("approvals")
        ]
        return sorted(
            [item for item in records if status is None or item.status == status],
            key=lambda item: item.requested_at,
            reverse=True,
        )

    async def transition(
        self,
        approval_id: str,
        *,
        expected_status: ApprovalStatus,
        updated: ApprovalRequest,
    ) -> ApprovalRequest:
        key = f"approvals/{approval_id}"

        def transition(documents: dict[str, Any]) -> dict[str, Any]:
            current = ApprovalRequest.model_validate(documents[key])
            if current.status != expected_status or current.version + 1 != updated.version:
                raise ApprovalConflictError(
                    f"Approval {approval_id} is already {current.status.value}"
                )
            if (
                updated.status == ApprovalStatus.APPROVED
                and datetime.now(UTC) >= current.expires_at
            ):
                raise ApprovalConflictError("Approval has expired")
            writes = {key: updated.model_dump(mode="json")}
            if updated.status == ApprovalStatus.APPROVED:
                event = DispatchEvent(
                    event_id=f"dispatch-{approval_id}",
                    approval_id=approval_id,
                    ticket_id=updated.ticket_id,
                    occurred_at=updated.decided_at or datetime.now(UTC),
                )
                writes[f"events/{event.event_id}"] = event.model_dump(mode="json")
            return writes

        await self.store.transact([key], transition)
        return updated

    async def events(self, *, unpublished_only: bool = False) -> builtins.list[DispatchEvent]:
        events = [DispatchEvent.model_validate(item) for item in await self.store.scan("events")]
        return [item for item in events if not unpublished_only or not item.published]

    async def published(self, event: DispatchEvent) -> None:
        key = f"events/{event.event_id}"

        def mark(documents: dict[str, Any]) -> dict[str, Any]:
            current = DispatchEvent.model_validate(documents[key])
            return {key: current.model_copy(update={"published": True}).model_dump(mode="json")}

        await self.store.transact([key], mark)

    async def delivery_failed(self, event: DispatchEvent, error: Exception) -> None:
        from datetime import timedelta

        key = f"events/{event.event_id}"

        def failed(documents: dict[str, Any]) -> dict[str, Any]:
            current = DispatchEvent.model_validate(documents[key])
            attempts = current.attempts + 1
            return {
                key: current.model_copy(
                    update={
                        "attempts": attempts,
                        "error_type": type(error).__name__,
                        "next_attempt_at": datetime.now(UTC)
                        + timedelta(seconds=min(600, 2**attempts)),
                    }
                ).model_dump(mode="json")
            }

        await self.store.transact([key], failed)

    async def assignments(self) -> builtins.list[Assignment]:
        return [Assignment.model_validate(item) for item in await self.store.scan("assignments")]

    async def revision(self) -> int:
        document = await self.store.get("dispatch/revision")
        return int(document["value"]) if document else 0

    async def finish(
        self,
        approval: ApprovalRequest,
        *,
        revision: int,
        assignment: Assignment | None,
        error: str | None = None,
    ) -> None:
        key = f"approvals/{approval.approval_id}"

        def finish(documents: dict[str, Any]) -> dict[str, Any]:
            current = ApprovalRequest.model_validate(documents[key])
            if current.status in {ApprovalStatus.EXECUTED, ApprovalStatus.FAILED}:
                return {}
            if current.status != ApprovalStatus.APPROVED:
                raise ApprovalConflictError("Dispatch requires an approved proposal")
            actual_revision = (documents["dispatch/revision"] or {}).get("value", 0)
            if actual_revision != revision:
                raise ApprovalConflictError("Dispatch state changed; retry validation")
            updates: dict[str, Any] = {
                "status": ApprovalStatus.EXECUTED if assignment else ApprovalStatus.FAILED,
                "version": current.version + 1,
                "execution_error": error,
            }
            writes: dict[str, Any] = {
                key: current.model_copy(update=updates).model_dump(mode="json"),
                "dispatch/revision": {"value": revision + 1},
                f"history/{approval.approval_id}": {
                    "event_id": approval.approval_id,
                    "event_type": "dispatch.completed" if assignment else "dispatch.failed",
                    "occurred_at": datetime.now(UTC).isoformat(),
                    "approval_id": approval.approval_id,
                    "ticket_id": approval.ticket_id,
                    "assignment_id": assignment.assignment_id if assignment else None,
                    "idempotency_key": approval.approval_id,
                    "success": assignment is not None,
                    "error_type": error,
                },
            }
            if assignment:
                writes[f"assignments/{assignment.ticket_id}"] = assignment.model_dump(mode="json")
            return writes

        await self.store.transact([key, "dispatch/revision"], finish)
