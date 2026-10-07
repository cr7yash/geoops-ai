"""Public API views for tickets and technicians."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from geoops_api.domain.models import (
    AssignmentStatus,
    GeoPoint,
    TechnicianStatus,
    TicketPriority,
    TicketStatus,
)


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PageMeta(ApiModel):
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class TicketSummary(ApiModel):
    ticket_id: str
    title: str
    priority: TicketPriority
    status: TicketStatus
    customer_name: str
    site_name: str
    city: str
    state: str
    equipment_type: str
    required_certification_ids: list[str]
    resolution_due_at: datetime
    sla_state: str
    assigned_technician_name: str | None


class TicketListResponse(PageMeta):
    items: list[TicketSummary]


class SiteView(ApiModel):
    site_id: str
    customer_id: str
    name: str
    address: str
    city: str
    state: str
    postal_code: str
    timezone: str
    location: GeoPoint | None
    geocode_status: str
    routing_mode: str


class AssignmentView(ApiModel):
    assignment_id: str
    ticket_id: str
    technician_id: str
    technician_name: str
    ticket_title: str | None = None
    scheduled_start: datetime
    scheduled_end: datetime
    status: AssignmentStatus
    created_at: datetime


class TicketDetail(ApiModel):
    ticket_id: str
    customer_id: str
    customer_name: str
    site_id: str
    site: SiteView
    title: str
    description: str
    equipment_type: str
    equipment_id: str
    required_certification_ids: list[str]
    priority: TicketPriority
    status: TicketStatus
    created_at: datetime
    response_due_at: datetime
    resolution_due_at: datetime
    sla_state: str
    assignments: list[AssignmentView]


class CertificationView(ApiModel):
    certification_id: str
    name: str
    expires_on: date
    validity: str


class TechnicianSummary(ApiModel):
    technician_id: str
    name: str
    email: str
    phone: str
    status: TechnicianStatus
    home_city: str
    current_location: GeoPoint
    skill_tags: list[str]
    completed_jobs: int
    average_rating: float
    certifications: list[CertificationView]
    active_assignment_count: int


class TechnicianListResponse(PageMeta):
    items: list[TechnicianSummary]


class TechnicianDetail(ApiModel):
    technician_id: str
    name: str
    email: str
    phone: str
    status: TechnicianStatus
    home_city: str
    current_location: GeoPoint
    skill_tags: list[str]
    completed_jobs: int
    average_rating: float
    certifications: list[CertificationView]
    assignments: list[AssignmentView]
