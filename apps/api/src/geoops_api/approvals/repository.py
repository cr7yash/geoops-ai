"""Process-local approval repository for development and tests."""

import asyncio

from geoops_api.approvals.interfaces import ApprovalConflictError
from geoops_api.approvals.models import ApprovalRequest
from geoops_api.domain.models import ApprovalStatus


class InMemoryApprovalRepository:
    def __init__(self) -> None:
        self._records: dict[str, ApprovalRequest] = {}
        self._lock = asyncio.Lock()

    async def create(self, approval: ApprovalRequest) -> ApprovalRequest:
        async with self._lock:
            if approval.approval_id in self._records:
                raise ApprovalConflictError(f"Approval {approval.approval_id} already exists")
            self._records[approval.approval_id] = approval
        return approval

    async def get(self, approval_id: str) -> ApprovalRequest | None:
        return self._records.get(approval_id)

    async def list(self, status: ApprovalStatus | None = None) -> list[ApprovalRequest]:
        records = list(self._records.values())
        if status is not None:
            records = [record for record in records if record.status == status]
        return sorted(records, key=lambda item: item.requested_at, reverse=True)

    async def transition(
        self,
        approval_id: str,
        *,
        expected_status: ApprovalStatus,
        updated: ApprovalRequest,
    ) -> ApprovalRequest:
        async with self._lock:
            current = self._records.get(approval_id)
            if current is None:
                raise KeyError(approval_id)
            if current.status != expected_status:
                raise ApprovalConflictError(
                    f"Approval {approval_id} is already {current.status.value}"
                )
            self._records[approval_id] = updated
        return updated
