"""Firestore adapter for operational approval state."""

from google.api_core.exceptions import AlreadyExists
from google.cloud.firestore_v1 import AsyncClient, AsyncTransaction, async_transactional

from geoops_api.approvals.interfaces import ApprovalConflictError
from geoops_api.approvals.models import ApprovalRequest
from geoops_api.domain.models import ApprovalStatus


class FirestoreApprovalRepository:
    """Persist approvals with transactional compare-and-set transitions."""

    def __init__(
        self,
        *,
        project: str,
        collection_name: str,
        client: AsyncClient | None = None,
    ) -> None:
        self._client = client or AsyncClient(project=project)
        self._collection = self._client.collection(collection_name)

    async def create(self, approval: ApprovalRequest) -> ApprovalRequest:
        try:
            await self._collection.document(approval.approval_id).create(
                approval.model_dump(mode="python")
            )
        except AlreadyExists as exc:
            raise ApprovalConflictError(f"Approval {approval.approval_id} already exists") from exc
        return approval

    async def get(self, approval_id: str) -> ApprovalRequest | None:
        snapshot = await self._collection.document(approval_id).get()
        if not snapshot.exists:
            return None
        return ApprovalRequest.model_validate(snapshot.to_dict())

    async def list(self, status: ApprovalStatus | None = None) -> list[ApprovalRequest]:
        records: list[ApprovalRequest] = []
        async for snapshot in self._collection.stream():
            record = ApprovalRequest.model_validate(snapshot.to_dict())
            if status is None or record.status == status:
                records.append(record)
        return sorted(records, key=lambda item: item.requested_at, reverse=True)

    async def transition(
        self,
        approval_id: str,
        *,
        expected_status: ApprovalStatus,
        updated: ApprovalRequest,
    ) -> ApprovalRequest:
        reference = self._collection.document(approval_id)
        transaction = self._client.transaction()

        @async_transactional
        async def apply_transition(current_transaction: AsyncTransaction) -> None:
            snapshot = await reference.get(transaction=current_transaction)
            if not snapshot.exists:
                raise KeyError(approval_id)
            current = ApprovalRequest.model_validate(snapshot.to_dict())
            if current.status != expected_status:
                raise ApprovalConflictError(
                    f"Approval {approval_id} is already {current.status.value}"
                )
            current_transaction.set(reference, updated.model_dump(mode="python"))

        await apply_transition(transaction)
        return updated
