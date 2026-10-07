"""Provider-neutral domain entities for operational and analytical data."""

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DomainModel(BaseModel):
    """Strict immutable base for domain records."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketStatus(StrEnum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TechnicianStatus(StrEnum):
    AVAILABLE = "available"
    DISPATCHED = "dispatched"
    OFF_DUTY = "off_duty"
    UNAVAILABLE = "unavailable"


class AssignmentStatus(StrEnum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SLAEventType(StrEnum):
    CREATED = "created"
    RESPONSE_DUE = "response_due"
    RESPONSE_MET = "response_met"
    RESOLUTION_DUE = "resolution_due"
    RESOLUTION_MET = "resolution_met"
    BREACHED = "breached"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"
    FAILED = "failed"


class GeoPoint(DomainModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class Customer(DomainModel):
    customer_id: str
    name: str
    industry: str
    service_tier: str
    active: bool = True


class Site(DomainModel):
    site_id: str
    customer_id: str
    name: str
    address: str
    city: str
    state: str
    postal_code: str
    timezone: str = "America/Los_Angeles"
    location: GeoPoint | None
    geocode_status: str = "valid"
    routing_mode: str = "normal"


class Certification(DomainModel):
    certification_id: str
    name: str
    issuing_body: str
    equipment_types: list[str]


class TechnicianCertification(DomainModel):
    technician_id: str
    certification_id: str
    issued_on: date
    expires_on: date


class Technician(DomainModel):
    technician_id: str
    name: str
    email: str
    phone: str
    status: TechnicianStatus
    home_city: str
    current_location: GeoPoint
    skill_tags: list[str]
    completed_jobs: int = Field(ge=0)
    average_rating: float = Field(ge=0, le=5)


class ServiceTicket(DomainModel):
    ticket_id: str
    customer_id: str
    site_id: str
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


class Assignment(DomainModel):
    assignment_id: str
    ticket_id: str
    technician_id: str
    scheduled_start: datetime
    scheduled_end: datetime
    status: AssignmentStatus
    created_at: datetime


class SLAEvent(DomainModel):
    event_id: str
    ticket_id: str
    event_type: SLAEventType
    occurred_at: datetime
    deadline_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentRun(DomainModel):
    agent_run_id: str
    session_id: str
    started_at: datetime
    completed_at: datetime | None = None
    status: str
    model: str | None = None
    tool_names: list[str] = Field(default_factory=list)


class EvaluationResult(DomainModel):
    evaluation_result_id: str
    evaluation_run_id: str
    case_id: str
    created_at: datetime
    task_success: bool
    metrics: dict[str, float] = Field(default_factory=dict)


class KnowledgeDocument(DomainModel):
    document_id: str
    customer_id: str | None = None
    title: str
    document_type: str
    storage_uri: str
    version: str
    effective_date: date | None = None


class KnowledgeChunk(DomainModel):
    chunk_id: str
    document_id: str
    customer_id: str | None = None
    equipment_type: str | None = None
    document_type: str
    version: str
    effective_date: date | None = None
    text: str
    embedding: list[float] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SeedDataset(DomainModel):
    seed_version: str
    reference_time: datetime
    customers: list[Customer]
    sites: list[Site]
    certifications: list[Certification]
    technician_certifications: list[TechnicianCertification]
    technicians: list[Technician]
    service_tickets: list[ServiceTicket]
    assignments: list[Assignment]
    sla_events: list[SLAEvent]
