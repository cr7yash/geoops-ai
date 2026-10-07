"""HTTP contracts for approval proposals and decisions."""

from pydantic import Field

from geoops_api.approvals.models import ApprovalRequest
from geoops_api.schemas.catalog import ApiModel


class CreateApprovalRequest(ApiModel):
    ticket_id: str = Field(min_length=1, max_length=50)
    technician_id: str = Field(min_length=1, max_length=50)
    reason: str = Field(min_length=3, max_length=500)
    requested_by: str = Field(min_length=2, max_length=100)


class ApprovalDecisionRequest(ApiModel):
    decided_by: str = Field(min_length=2, max_length=100)
    comment: str | None = Field(default=None, max_length=500)


class ApprovalListResponse(ApiModel):
    items: list[ApprovalRequest]
    total: int = Field(ge=0)
