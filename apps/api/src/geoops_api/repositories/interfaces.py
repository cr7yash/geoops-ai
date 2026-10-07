"""Provider-neutral repository interfaces used by application services."""

from typing import Protocol

from geoops_api.domain.models import (
    Assignment,
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


class CatalogRepository(Protocol):
    """Read-only Phase 2 operational catalog boundary."""

    @property
    def dataset(self) -> SeedDataset: ...

    async def list_tickets(
        self,
        *,
        status: TicketStatus | None = None,
        priority: TicketPriority | None = None,
        query: str | None = None,
    ) -> list[ServiceTicket]: ...

    async def get_ticket(self, ticket_id: str) -> ServiceTicket | None: ...

    async def list_technicians(
        self,
        *,
        status: TechnicianStatus | None = None,
        certification_id: str | None = None,
        query: str | None = None,
    ) -> list[Technician]: ...

    async def get_technician(self, technician_id: str) -> Technician | None: ...

    async def get_customer(self, customer_id: str) -> Customer | None: ...

    async def get_site(self, site_id: str) -> Site | None: ...

    async def list_certifications(self) -> list[Certification]: ...

    async def list_technician_certifications(
        self, technician_id: str
    ) -> list[TechnicianCertification]: ...

    async def list_assignments_for_ticket(self, ticket_id: str) -> list[Assignment]: ...

    async def list_assignments_for_technician(self, technician_id: str) -> list[Assignment]: ...
