"""Deterministic eligibility and route-aware ranking for technician dispatch."""

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
from geoops_api.maps.interfaces import MapsProvider
from geoops_api.maps.models import (
    MapsProviderError,
    RouteElementStatus,
    RouteMatrixElement,
    RouteWaypoint,
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
    version: str = "dispatch-v2-routes"
    maximum_distance_km: float = 65.0
    maximum_travel_minutes: float = 120.0
    service_duration: timedelta = timedelta(hours=4)
    lead_time: timedelta = timedelta(hours=1)


class TicketNotDispatchableError(ValueError):
    """Raised when recommendations do not make sense for a closed ticket."""


class DispatchService:
    """Apply hard eligibility gates, route evidence, then a stable score."""

    def __init__(
        self,
        repository: CatalogRepository,
        maps_provider: MapsProvider,
        policy: DispatchPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._maps_provider = maps_provider
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

        preliminary_eligible: list[DispatchCandidate] = []
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
            (preliminary_eligible if candidate.eligible else excluded).append(candidate)

        eligible, route_excluded = await self._route_and_score_candidates(
            candidates=preliminary_eligible,
            destination=site.location,
            destination_id=site.site_id,
            departure_time=window_start,
        )
        excluded.extend(route_excluded)
        eligible.sort(
            key=lambda item: (
                -(item.score or 0),
                item.travel_duration_minutes
                if item.travel_duration_minutes is not None
                else float("inf"),
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
            maximum_travel_minutes=self._policy.maximum_travel_minutes,
            maps_provider=self._maps_provider.name,
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

        straight_line_distance_km: float | None = None
        if site_location is None:
            reasons.append(DispatchExclusionReason.SITE_LOCATION_UNAVAILABLE)
        else:
            straight_line_distance_km = round(
                self._haversine_km(technician.current_location, site_location), 1
            )
            if straight_line_distance_km > self._policy.maximum_distance_km:
                reasons.append(DispatchExclusionReason.OUTSIDE_SERVICE_RADIUS)

        active_assignment_count = sum(
            assignment.scheduled_end > window_start for assignment in relevant_assignments
        )
        return DispatchCandidate(
            technician_id=technician.technician_id,
            technician_name=technician.name,
            status=technician.status,
            eligible=not reasons,
            exclusion_reasons=reasons,
            straight_line_distance_km=straight_line_distance_km,
            active_assignment_count=active_assignment_count,
            matched_certification_ids=matched,
        )

    async def _route_and_score_candidates(
        self,
        *,
        candidates: list[DispatchCandidate],
        destination: GeoPoint | None,
        destination_id: str,
        departure_time: datetime,
    ) -> tuple[list[DispatchCandidate], list[DispatchCandidate]]:
        if not candidates or destination is None:
            return candidates, []
        technicians = {
            technician.technician_id: technician
            for technician in self._repository.dataset.technicians
        }
        origins = [
            RouteWaypoint(
                waypoint_id=candidate.technician_id,
                location=technicians[candidate.technician_id].current_location,
            )
            for candidate in candidates
        ]
        route_is_estimate: bool | None = None
        try:
            matrix = await self._maps_provider.compute_route_matrix(
                origins,
                [RouteWaypoint(waypoint_id=destination_id, location=destination)],
                departure_time=departure_time,
            )
            route_is_estimate = matrix.is_estimate
            elements = {item.origin_id: item for item in matrix.elements}
        except MapsProviderError:
            elements = {}

        eligible: list[DispatchCandidate] = []
        excluded: list[DispatchCandidate] = []
        for candidate in candidates:
            element = elements.get(candidate.technician_id)
            if not self._route_succeeded(element):
                excluded.append(
                    candidate.model_copy(
                        update={
                            "eligible": False,
                            "exclusion_reasons": [DispatchExclusionReason.ROUTE_UNAVAILABLE],
                            "route_provider": self._maps_provider.name,
                            "route_is_estimate": route_is_estimate,
                        }
                    )
                )
                continue
            assert element is not None
            assert element.distance_km is not None
            assert element.duration_minutes is not None
            route_values = {
                "distance_km": element.distance_km,
                "travel_duration_minutes": element.duration_minutes,
                "route_provider": self._maps_provider.name,
                "route_is_estimate": route_is_estimate,
            }
            if element.duration_minutes > self._policy.maximum_travel_minutes:
                excluded.append(
                    candidate.model_copy(
                        update={
                            **route_values,
                            "eligible": False,
                            "exclusion_reasons": [
                                DispatchExclusionReason.EXCEEDS_MAXIMUM_TRAVEL_TIME
                            ],
                        }
                    )
                )
                continue
            technician = technicians[candidate.technician_id]
            breakdown = self._score_candidate(
                technician=technician,
                active_assignment_count=candidate.active_assignment_count,
                travel_duration_minutes=element.duration_minutes,
            )
            score = round(
                breakdown.certification
                + breakdown.travel_time
                + breakdown.workload
                + breakdown.performance
                + breakdown.experience,
                2,
            )
            eligible.append(
                candidate.model_copy(
                    update={
                        **route_values,
                        "score": score,
                        "score_breakdown": breakdown,
                    }
                )
            )
        return eligible, excluded

    def _score_candidate(
        self,
        *,
        technician: Technician,
        active_assignment_count: int,
        travel_duration_minutes: float,
    ) -> DispatchScoreBreakdown:
        return DispatchScoreBreakdown(
            certification=25.0,
            travel_time=round(
                30
                * max(
                    0,
                    1 - travel_duration_minutes / self._policy.maximum_travel_minutes,
                ),
                2,
            ),
            workload=round(20 * max(0, 1 - active_assignment_count / 3), 2),
            performance=round(15 * technician.average_rating / 5, 2),
            experience=round(10 * min(technician.completed_jobs / 200, 1), 2),
        )

    @staticmethod
    def _route_succeeded(element: RouteMatrixElement | None) -> bool:
        return (
            element is not None
            and element.status == RouteElementStatus.OK
            and element.distance_km is not None
            and element.duration_minutes is not None
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
