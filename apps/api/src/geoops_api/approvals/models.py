"""Operational approval records stored in memory or Firestore."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from geoops_api.domain.models import ApprovalStatus


class ApprovalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ApprovalAction(StrEnum):
    ASSIGN_TECHNICIAN = "assign_technician"


class ApprovalEvidence(ApprovalModel):
    policy_version: str
    score: float = Field(ge=0)
    distance_km: float | None = Field(default=None, ge=0)
    travel_duration_minutes: float | None = Field(default=None, ge=0)
    route_provider: str | None = None
    route_is_estimate: bool | None = None
    matched_certification_ids: list[str] = Field(default_factory=list)


class ApprovalRequest(ApprovalModel):
    approval_id: str
    action: ApprovalAction
    ticket_id: str
    ticket_title: str
    from_technician_id: str | None = None
    from_technician_name: str | None = None
    to_technician_id: str
    to_technician_name: str
    reason: str
    status: ApprovalStatus
    requested_by: str
    requested_at: datetime
    expires_at: datetime
    decided_by: str | None = None
    decided_at: datetime | None = None
    decision_comment: str | None = None
    evidence: ApprovalEvidence
    version: int = Field(default=1, ge=1)
