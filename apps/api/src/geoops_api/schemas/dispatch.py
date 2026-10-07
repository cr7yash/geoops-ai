"""Public schemas for deterministic dispatch recommendations."""

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from geoops_api.domain.models import TechnicianStatus, TicketPriority
from geoops_api.schemas.catalog import ApiModel


class DispatchExclusionReason(StrEnum):
    UNAVAILABLE = "unavailable"
    MISSING_REQUIRED_CERTIFICATION = "missing_required_certification"
    EXPIRED_REQUIRED_CERTIFICATION = "expired_required_certification"
    SCHEDULE_CONFLICT = "schedule_conflict"
    SITE_LOCATION_UNAVAILABLE = "site_location_unavailable"
    OUTSIDE_SERVICE_RADIUS = "outside_service_radius"
    ROUTE_UNAVAILABLE = "route_unavailable"
    EXCEEDS_MAXIMUM_TRAVEL_TIME = "exceeds_maximum_travel_time"


class DispatchScoreBreakdown(ApiModel):
    certification: float = Field(ge=0, le=25)
    travel_time: float = Field(ge=0, le=30)
    workload: float = Field(ge=0, le=20)
    performance: float = Field(ge=0, le=15)
    experience: float = Field(ge=0, le=10)


class DispatchCandidate(ApiModel):
    rank: int | None = Field(default=None, ge=1)
    technician_id: str
    technician_name: str
    status: TechnicianStatus
    eligible: bool
    exclusion_reasons: list[DispatchExclusionReason]
    straight_line_distance_km: float | None = Field(default=None, ge=0)
    distance_km: float | None = Field(default=None, ge=0)
    travel_duration_minutes: float | None = Field(default=None, ge=0)
    route_provider: str | None = None
    route_is_estimate: bool | None = None
    active_assignment_count: int = Field(ge=0)
    matched_certification_ids: list[str]
    score: float | None = Field(default=None, ge=0, le=100)
    score_breakdown: DispatchScoreBreakdown | None = None


class DispatchRecommendationResponse(ApiModel):
    ticket_id: str
    ticket_title: str
    priority: TicketPriority
    sla_state: str
    policy_version: str
    evaluated_at: datetime
    service_window_start: datetime
    service_window_end: datetime
    maximum_distance_km: float = Field(gt=0)
    maximum_travel_minutes: float = Field(gt=0)
    maps_provider: str
    required_certification_ids: list[str]
    recommended_technician_id: str | None
    eligible_candidates: list[DispatchCandidate]
    excluded_candidates: list[DispatchCandidate]
    total_evaluated: int = Field(ge=0)
