"""Approval persistence construction."""

from geoops_api.approvals.firestore import FirestoreApprovalRepository
from geoops_api.approvals.repository import InMemoryApprovalRepository
from geoops_api.config import Settings
from geoops_api.state import SQLiteDocumentStore
from geoops_api.workflow import WorkflowRepository


def build_approval_repository(settings: Settings) -> WorkflowRepository:
    if settings.approval_store == "memory":
        return InMemoryApprovalRepository()
    if settings.approval_store == "sqlite":
        return WorkflowRepository(SQLiteDocumentStore(str(settings.state_database_path)))
    assert settings.google_cloud_project is not None
    return FirestoreApprovalRepository(
        project=settings.google_cloud_project,
        collection_name=settings.firestore_approvals_collection,
    )
