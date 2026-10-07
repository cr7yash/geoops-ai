"""Read services that enrich domain records without coupling to storage."""

from datetime import date, datetime, timedelta

from geoops_api.domain.models import (
    AssignmentStatus,
    TechnicianStatus,
    TicketPriority,
    TicketStatus,
)
from geoops_api.repositories.interfaces import CatalogRepository
from geoops_api.schemas.catalog import (
    AssignmentView,
    CertificationView,
    SiteView,
    TechnicianDetail,
    TechnicianListResponse,
    TechnicianSummary,
    TicketDetail,
    TicketListResponse,
    TicketSummary,
)


class CatalogService:
    """Compose repository records into stable API views."""

    def __init__(self, repository: CatalogRepository) -> None:
        self._repository = repository

    async def list_tickets(
        self,
        *,
        status: TicketStatus | None,
        priority: TicketPriority | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> TicketListResponse:
        tickets = await self._repository.list_tickets(status=status, priority=priority, query=query)
        assignments_by_ticket = {
            assignment.ticket_id: assignment
            for assignment in self._repository.dataset.assignments
            if assignment.status in {AssignmentStatus.ACTIVE, AssignmentStatus.SCHEDULED}
        }
        technicians = {
            technician.technician_id: technician
            for technician in self._repository.dataset.technicians
        }
        customers = {
            customer.customer_id: customer for customer in self._repository.dataset.customers
        }
        sites = {site.site_id: site for site in self._repository.dataset.sites}
        summaries = [
            TicketSummary(
                ticket_id=ticket.ticket_id,
                title=ticket.title,
                priority=ticket.priority,
                status=ticket.status,
                customer_name=customers[ticket.customer_id].name,
                site_name=sites[ticket.site_id].name,
                city=sites[ticket.site_id].city,
                state=sites[ticket.site_id].state,
                equipment_type=ticket.equipment_type,
                required_certification_ids=ticket.required_certification_ids,
                resolution_due_at=ticket.resolution_due_at,
                sla_state=self._sla_state(
                    status=ticket.status,
                    due_at=ticket.resolution_due_at,
                    reference_time=self._repository.dataset.reference_time,
                ),
                assigned_technician_name=(
                    technicians[assignments_by_ticket[ticket.ticket_id].technician_id].name
                    if ticket.ticket_id in assignments_by_ticket
                    else None
                ),
            )
            for ticket in tickets
        ]
        return TicketListResponse(
            items=summaries[offset : offset + limit],
            total=len(summaries),
            limit=limit,
            offset=offset,
        )

    async def get_ticket(self, ticket_id: str) -> TicketDetail | None:
        ticket = await self._repository.get_ticket(ticket_id)
        if ticket is None:
            return None
        customer = await self._repository.get_customer(ticket.customer_id)
        site = await self._repository.get_site(ticket.site_id)
        if customer is None or site is None:
            return None
        assignment_records = await self._repository.list_assignments_for_ticket(ticket_id)
        technician_names = {
            technician.technician_id: technician.name
            for technician in self._repository.dataset.technicians
        }
        return TicketDetail(
            **ticket.model_dump(),
            customer_name=customer.name,
            site=SiteView.model_validate(site.model_dump()),
            sla_state=self._sla_state(
                status=ticket.status,
                due_at=ticket.resolution_due_at,
                reference_time=self._repository.dataset.reference_time,
            ),
            assignments=[
                AssignmentView(
                    **assignment.model_dump(),
                    technician_name=technician_names[assignment.technician_id],
                )
                for assignment in assignment_records
            ],
        )

    async def list_technicians(
        self,
        *,
        status: TechnicianStatus | None,
        certification_id: str | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> TechnicianListResponse:
        technicians = await self._repository.list_technicians(
            status=status, certification_id=certification_id, query=query
        )
        certification_names = {
            item.certification_id: item.name for item in self._repository.dataset.certifications
        }
        certification_records = self._repository.dataset.technician_certifications
        active_assignments = self._repository.dataset.assignments
        summaries: list[TechnicianSummary] = []
        for technician in technicians:
            technician_certifications = [
                item
                for item in certification_records
                if item.technician_id == technician.technician_id
            ]
            summaries.append(
                TechnicianSummary(
                    **technician.model_dump(),
                    certifications=[
                        CertificationView(
                            certification_id=item.certification_id,
                            name=certification_names[item.certification_id],
                            expires_on=item.expires_on,
                            validity=self._certification_validity(item.expires_on),
                        )
                        for item in technician_certifications
                    ],
                    active_assignment_count=sum(
                        assignment.technician_id == technician.technician_id
                        and assignment.status
                        in {AssignmentStatus.ACTIVE, AssignmentStatus.SCHEDULED}
                        for assignment in active_assignments
                    ),
                )
            )
        return TechnicianListResponse(
            items=summaries[offset : offset + limit],
            total=len(summaries),
            limit=limit,
            offset=offset,
        )

    async def get_technician(self, technician_id: str) -> TechnicianDetail | None:
        technician = await self._repository.get_technician(technician_id)
        if technician is None:
            return None
        certification_names = {
            item.certification_id: item.name for item in self._repository.dataset.certifications
        }
        certification_records = await self._repository.list_technician_certifications(technician_id)
        assignment_records = await self._repository.list_assignments_for_technician(technician_id)
        ticket_titles = {
            ticket.ticket_id: ticket.title for ticket in self._repository.dataset.service_tickets
        }
        return TechnicianDetail(
            **technician.model_dump(),
            certifications=[
                CertificationView(
                    certification_id=item.certification_id,
                    name=certification_names[item.certification_id],
                    expires_on=item.expires_on,
                    validity=self._certification_validity(item.expires_on),
                )
                for item in certification_records
            ],
            assignments=[
                AssignmentView(
                    **assignment.model_dump(),
                    technician_name=technician.name,
                    ticket_title=ticket_titles[assignment.ticket_id],
                )
                for assignment in assignment_records
            ],
        )

    def _certification_validity(self, expires_on: date) -> str:
        reference_date = self._repository.dataset.reference_time.date()
        days_remaining = (expires_on - reference_date).days
        if days_remaining < 0:
            return "expired"
        if days_remaining <= 30:
            return "expiring_soon"
        return "valid"

    @staticmethod
    def _sla_state(*, status: TicketStatus, due_at: datetime, reference_time: datetime) -> str:
        if status == TicketStatus.COMPLETED:
            return "met"
        if due_at < reference_time:
            return "overdue"
        if due_at <= reference_time + timedelta(hours=4):
            return "at_risk"
        return "on_track"
