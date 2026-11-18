"""Firestore operational workflow adapter."""

from geoops_api.state import FirestoreDocumentStore
from geoops_api.workflow import WorkflowRepository


class FirestoreApprovalRepository(WorkflowRepository):
    def __init__(self, *, project: str, collection_name: str) -> None:
        super().__init__(FirestoreDocumentStore(project, namespace=collection_name))
