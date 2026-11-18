"""Deterministic JSON-backed repository for local development and tests."""

import json
from pathlib import Path

from geoops_api.domain.models import (
    Assignment,
    AssignmentStatus,
    Certification,
    Customer,
    SeedDataset,
    ServiceTicket,
    Site,
    Technician,
    TechnicianCertification,
    TechnicianStatus,
    TicketPriority,
    TicketStatus,
)
from geoops_api.workflow import WorkflowRepository


class JsonCatalogRepository:
    """Load the seed snapshot once and expose async read operations."""

    def __init__(self, seed_path: Path, workflow: WorkflowRepository | None = None) -> None:
        if not seed_path.is_file():
            raise FileNotFoundError(
                f"Seed dataset not found at {seed_path}. Run `make seed` before starting the API."
            )
        payload = json.loads(seed_path.read_text(encoding="utf-8"))
        self._dataset = SeedDataset.model_validate(payload)
        self._seed = self._dataset
        self._workflow = workflow
        self._customers = {item.customer_id: item for item in self._dataset.customers}
        self._sites = {item.site_id: item for item in self._dataset.sites}
        self._tickets = {item.ticket_id: item for item in self._dataset.service_tickets}
        self._technicians = {item.technician_id: item for item in self._dataset.technicians}

    @property
    def dataset(self) -> SeedDataset:
        return self._dataset

    async def refresh(self) -> None:
        if self._workflow is None:
            return
        overrides = {item.ticket_id: item for item in await self._workflow.assignments()}
        assignments = [
            item.model_copy(update={"status": AssignmentStatus.CANCELLED})
            if item.ticket_id in overrides
            and item.status in {AssignmentStatus.ACTIVE, AssignmentStatus.SCHEDULED}
            else item
            for item in self._seed.assignments
        ] + list(overrides.values())
        tickets = [
            item.model_copy(update={"status": TicketStatus.ASSIGNED})
            if item.ticket_id in overrides
            else item
            for item in self._seed.service_tickets
        ]
        self._dataset = self._seed.model_copy(
            update={"assignments": assignments, "service_tickets": tickets}
        )
        self._tickets = {item.ticket_id: item for item in tickets}

    async def list_tickets(
        self,
        *,
        status: TicketStatus | None = None,
        priority: TicketPriority | None = None,
        query: str | None = None,
    ) -> list[ServiceTicket]:
        await self.refresh()
        tickets = self._dataset.service_tickets
        if status is not None:
            tickets = [item for item in tickets if item.status == status]
        if priority is not None:
            tickets = [item for item in tickets if item.priority == priority]
        if query:
            needle = query.casefold().strip()
            tickets = [
                item
                for item in tickets
                if needle
                in " ".join(
                    (
                        item.ticket_id,
                        item.title,
                        item.description,
                        item.equipment_type,
                    )
                ).casefold()
            ]
        return sorted(tickets, key=lambda item: (item.resolution_due_at, item.ticket_id))

    async def get_ticket(self, ticket_id: str) -> ServiceTicket | None:
        await self.refresh()
        return self._tickets.get(ticket_id)

    async def list_technicians(
        self,
        *,
        status: TechnicianStatus | None = None,
        certification_id: str | None = None,
        query: str | None = None,
    ) -> list[Technician]:
        await self.refresh()
        technicians = self._dataset.technicians
        if status is not None:
            technicians = [item for item in technicians if item.status == status]
        if certification_id:
            qualified_ids = {
                item.technician_id
                for item in self._dataset.technician_certifications
                if item.certification_id == certification_id
            }
            technicians = [item for item in technicians if item.technician_id in qualified_ids]
        if query:
            needle = query.casefold().strip()
            technicians = [
                item
                for item in technicians
                if needle
                in " ".join(
                    (item.technician_id, item.name, item.home_city, *item.skill_tags)
                ).casefold()
            ]
        return sorted(technicians, key=lambda item: item.name)

    async def get_technician(self, technician_id: str) -> Technician | None:
        await self.refresh()
        return self._technicians.get(technician_id)

    async def get_customer(self, customer_id: str) -> Customer | None:
        return self._customers.get(customer_id)

    async def get_site(self, site_id: str) -> Site | None:
        return self._sites.get(site_id)

    async def list_certifications(self) -> list[Certification]:
        return sorted(self._dataset.certifications, key=lambda item: item.name)

    async def list_technician_certifications(
        self, technician_id: str
    ) -> list[TechnicianCertification]:
        return [
            item
            for item in self._dataset.technician_certifications
            if item.technician_id == technician_id
        ]

    async def list_assignments_for_ticket(self, ticket_id: str) -> list[Assignment]:
        await self.refresh()
        return sorted(
            [item for item in self._dataset.assignments if item.ticket_id == ticket_id],
            key=lambda item: item.scheduled_start,
        )

    async def list_assignments_for_technician(self, technician_id: str) -> list[Assignment]:
        await self.refresh()
        return sorted(
            [item for item in self._dataset.assignments if item.technician_id == technician_id],
            key=lambda item: item.scheduled_start,
        )
