"""Isolated in-memory adapter for tests and temporary sessions."""

from geoops_api.state import SQLiteDocumentStore
from geoops_api.workflow import WorkflowRepository


class InMemoryApprovalRepository(WorkflowRepository):
    def __init__(self) -> None:
        super().__init__(SQLiteDocumentStore())
