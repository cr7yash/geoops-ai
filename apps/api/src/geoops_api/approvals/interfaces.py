"""Persistence port for short-lived human approval state."""

from typing import Protocol

from geoops_api.approvals.models import ApprovalRequest
from geoops_api.domain.models import ApprovalStatus


class ApprovalConflictError(RuntimeError):
    """Raised when a concurrent or invalid transition loses the race."""


class ApprovalRepository(Protocol):
    async def create(self, approval: ApprovalRequest) -> ApprovalRequest: ...

    async def get(self, approval_id: str) -> ApprovalRequest | None: ...

    async def list(self, status: ApprovalStatus | None = None) -> list[ApprovalRequest]: ...

    async def transition(
        self,
        approval_id: str,
        *,
        expected_status: ApprovalStatus,
        updated: ApprovalRequest,
    ) -> ApprovalRequest: ...
