"""Deterministic eligibility and ranking for technician dispatch."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt

from geoops_api.domain.models import (
    Assignment,
    AssignmentStatus,
    GeoPoint,
    ServiceTicket,
    Technician,
    TechnicianCertification,
    TechnicianStatus,
    TicketStatus,
)
from geoops_api.repositories.interfaces import CatalogRepository
from geoops_api.schemas.dispatch import (
    DispatchCandidate,
    DispatchExclusionReason,
    DispatchRecommendationResponse,
    DispatchScoreBreakdown,
)
from geoops_api.services.catalog import CatalogService


@dataclass(frozen=True)
class DispatchPolicy:
    version: str = "dispatch-v1"
    maximum_distance_km: float = 65.0
    service_duration: timedelta = timedelta(hours=4)
    lead_time: timedelta = timedelta(hours=1)


class TicketNotDispatchableError(ValueError):
    """Raised when recommendations do not make sense for a closed ticket."""


class DispatchService:
    """Apply hard eligibility gates before producing an explainable score."""

    def __init__(
        self,
        repository: CatalogRepository,
        policy: DispatchPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._policy = policy or DispatchPolicy()

    async def recommend(self, ticket_id: str) -> DispatchRecommendationResponse | None:
        ticket = await self._repository.get_ticket(ticket_id)
        if ticket is None:
            return None
        if ticket.status in {TicketStatus.COMPLETED, TicketStatus.CANCELLED}:
            raise TicketNotDispatchableError(
                f"Ticket {ticket_id} is {ticket.status.value} and cannot be dispatched"
            )

        site = await self._repository.get_site(ticket.site_id)
        if site is None:
            return None

        evaluated_at = self._repository.dataset.reference_time
        window_start = evaluated_at + self._policy.lead_time
        window_end = window_start + self._policy.service_duration
        assignments = self._repository.dataset.assignments
        certifications_by_technician = self._certifications_by_technician()

        eligible: list[DispatchCandidate] = []
        excluded: list[DispatchCandidate] = []
        for technician in self._repository.dataset.technicians:
            candidate = self._assess_candidate(
                ticket=ticket,
                technician=technician,
                technician_certifications=certifications_by_technician.get(
                    technician.technician_id, []
                ),
                assignments=assignments,
                site_location=site.location,
                window_start=window_start,
                window_end=window_end,
            )
            (eligible if candidate.eligible else excluded).append(candidate)

        eligible.sort(
            key=lambda item: (
                -(item.score or 0),
                item.distance_km if item.distance_km is not None else float("inf"),
                item.technician_id,
            )
        )
        ranked = [
            candidate.model_copy(update={"rank": rank})
            for rank, candidate in enumerate(eligible, 1)
        ]
        excluded.sort(key=lambda item: item.technician_name)

        sla_state = CatalogService._sla_state(
            status=ticket.status,
            due_at=ticket.resolution_due_at,
            reference_time=evaluated_at,
        )
        return DispatchRecommendationResponse(
            ticket_id=ticket.ticket_id,
            ticket_title=ticket.title,
            priority=ticket.priority,
            sla_state=sla_state,
            policy_version=self._policy.version,
            evaluated_at=evaluated_at,
            service_window_start=window_start,
            service_window_end=window_end,
            maximum_distance_km=self._policy.maximum_distance_km,
            required_certification_ids=ticket.required_certification_ids,
            recommended_technician_id=(ranked[0].technician_id if ranked else None),
            eligible_candidates=ranked,
            excluded_candidates=excluded,
            total_evaluated=len(ranked) + len(excluded),
        )

    def _assess_candidate(
        self,
        *,
        ticket: ServiceTicket,
        technician: Technician,
        technician_certifications: list[TechnicianCertification],
        assignments: list[Assignment],
        site_location: GeoPoint | None,
        window_start: datetime,
        window_end: datetime,
    ) -> DispatchCandidate:
        reasons: list[DispatchExclusionReason] = []
        if technician.status != TechnicianStatus.AVAILABLE:
            reasons.append(DispatchExclusionReason.UNAVAILABLE)

        required = set(ticket.required_certification_ids)
        held = {item.certification_id for item in technician_certifications}
        valid = {
            item.certification_id
            for item in technician_certifications
            if item.expires_on >= window_start.date()
        }
        matched = sorted(required & valid)
        if required - held:
            reasons.append(DispatchExclusionReason.MISSING_REQUIRED_CERTIFICATION)
        elif required - valid:
            reasons.append(DispatchExclusionReason.EXPIRED_REQUIRED_CERTIFICATION)

        relevant_assignments = [
            assignment
            for assignment in assignments
            if assignment.technician_id == technician.technician_id
            and assignment.ticket_id != ticket.ticket_id
            and assignment.status in {AssignmentStatus.ACTIVE, AssignmentStatus.SCHEDULED}
        ]
        if any(
            self._windows_overlap(
                window_start,
                window_end,
                assignment.scheduled_start,
                assignment.scheduled_end,
            )
            for assignment in relevant_assignments
        ):
            reasons.append(DispatchExclusionReason.SCHEDULE_CONFLICT)

        distance_km: float | None = None
        if site_location is None:
            reasons.append(DispatchExclusionReason.SITE_LOCATION_UNAVAILABLE)
        else:
            distance_km = round(self._haversine_km(technician.current_location, site_location), 1)
            if distance_km > self._policy.maximum_distance_km:
                reasons.append(DispatchExclusionReason.OUTSIDE_SERVICE_RADIUS)

        active_assignment_count = sum(
            assignment.scheduled_end > window_start for assignment in relevant_assignments
        )
        if reasons:
            return DispatchCandidate(
                technician_id=technician.technician_id,
                technician_name=technician.name,
                status=technician.status,
                eligible=False,
                exclusion_reasons=reasons,
                distance_km=distance_km,
                active_assignment_count=active_assignment_count,
                matched_certification_ids=matched,
            )

        assert distance_km is not None
        breakdown = DispatchScoreBreakdown(
            certification=25.0,
            proximity=round(30 * (1 - distance_km / self._policy.maximum_distance_km), 2),
            workload=round(20 * max(0, 1 - active_assignment_count / 3), 2),
            performance=round(15 * technician.average_rating / 5, 2),
            experience=round(10 * min(technician.completed_jobs / 200, 1), 2),
        )
        score = round(
            breakdown.certification
            + breakdown.proximity
            + breakdown.workload
            + breakdown.performance
            + breakdown.experience,
            2,
        )
        return DispatchCandidate(
            technician_id=technician.technician_id,
            technician_name=technician.name,
            status=technician.status,
            eligible=True,
            exclusion_reasons=[],
            distance_km=distance_km,
            active_assignment_count=active_assignment_count,
            matched_certification_ids=matched,
            score=score,
            score_breakdown=breakdown,
        )

    def _certifications_by_technician(self) -> dict[str, list[TechnicianCertification]]:
        grouped: dict[str, list[TechnicianCertification]] = {}
        for certification in self._repository.dataset.technician_certifications:
            grouped.setdefault(certification.technician_id, []).append(certification)
        return grouped

    @staticmethod
    def _windows_overlap(
        start_a: datetime,
        end_a: datetime,
        start_b: datetime,
        end_b: datetime,
    ) -> bool:
        return start_a < end_b and start_b < end_a

    @staticmethod
    def _haversine_km(origin: GeoPoint, destination: GeoPoint) -> float:
        earth_radius_km = 6371.0088
        origin_latitude = radians(origin.latitude)
        destination_latitude = radians(destination.latitude)
        latitude_delta = destination_latitude - origin_latitude
        longitude_delta = radians(destination.longitude - origin.longitude)
        value = sin(latitude_delta / 2) ** 2 + (
            cos(origin_latitude) * cos(destination_latitude) * sin(longitude_delta / 2) ** 2
        )
        return 2 * earth_radius_km * asin(sqrt(value))
