"""Approval persistence construction."""

from geoops_api.approvals.firestore import FirestoreApprovalRepository
from geoops_api.approvals.interfaces import ApprovalRepository
from geoops_api.approvals.repository import InMemoryApprovalRepository
from geoops_api.config import Settings


def build_approval_repository(settings: Settings) -> ApprovalRepository:
    if settings.approval_store == "memory":
        return InMemoryApprovalRepository()
    assert settings.google_cloud_project is not None
    return FirestoreApprovalRepository(
        project=settings.google_cloud_project,
        collection_name=settings.firestore_approvals_collection,
    )
