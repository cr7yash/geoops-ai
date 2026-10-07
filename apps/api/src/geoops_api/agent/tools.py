"""Validated read-only tools exposed to agent runtimes."""

import logging
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from geoops_api.domain.models import TechnicianStatus, TicketPriority, TicketStatus
from geoops_api.knowledge.models import DocumentType, KnowledgeFilters
from geoops_api.knowledge.service import KnowledgeService
from geoops_api.schemas.agent import AgentToolUse
from geoops_api.schemas.knowledge import KnowledgeSource
from geoops_api.services.catalog import CatalogService
from geoops_api.services.dispatch import DispatchService

logger = logging.getLogger("geoops.agent.tools")


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GetTicketInput(ToolInput):
    ticket_id: str = Field(min_length=1, max_length=50)


class SearchTicketsInput(ToolInput):
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    query: str | None = Field(default=None, min_length=1, max_length=100)
    limit: int = Field(default=10, ge=1, le=25)


class GetTechnicianInput(ToolInput):
    technician_id: str = Field(min_length=1, max_length=50)


class SearchTechniciansInput(ToolInput):
    status: TechnicianStatus | None = None
    certification_id: str | None = Field(default=None, max_length=50)
    query: str | None = Field(default=None, min_length=1, max_length=100)
    limit: int = Field(default=10, ge=1, le=25)


class RecommendAssignmentInput(ToolInput):
    ticket_id: str = Field(min_length=1, max_length=50)


class SearchKnowledgeInput(ToolInput):
    query: str = Field(min_length=3, max_length=500)
    customer_id: str | None = Field(default=None, max_length=50)
    equipment_type: str | None = Field(default=None, max_length=100)
    document_type: DocumentType | None = None
    limit: int = Field(default=5, ge=1, le=10)


class ToolOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: dict[str, Any]
    summary: str
    sources: list[KnowledgeSource] = Field(default_factory=list)
    retrieval_count: int | None = Field(default=None, ge=0)


type ToolHandler[InputT: ToolInput] = Callable[[InputT], Awaitable[ToolOutput]]


class AgentTool[InputT: ToolInput]:
    def __init__(
        self,
        *,
        name: str,
        description: str,
        input_model: type[InputT],
        handler: ToolHandler[InputT],
    ) -> None:
        self.name = name
        self.description = description
        self.input_model = input_model
        self.handler = handler


class ToolExecutionError(RuntimeError):
    """Raised when a model supplies an invalid tool call."""


class AgentToolRegistry:
    """The only route from an agent runtime to application data."""

    def __init__(
        self,
        *,
        catalog_service: CatalogService,
        dispatch_service: DispatchService,
        knowledge_service: KnowledgeService,
    ) -> None:
        self._catalog = catalog_service
        self._dispatch = dispatch_service
        self._knowledge = knowledge_service
        self._tools: dict[str, AgentTool[Any]] = {
            "get_ticket": AgentTool(
                name="get_ticket",
                description="Get one service ticket with site, SLA, and assignment data.",
                input_model=GetTicketInput,
                handler=self._get_ticket,
            ),
            "search_tickets": AgentTool(
                name="search_tickets",
                description="Search service tickets using operational filters.",
                input_model=SearchTicketsInput,
                handler=self._search_tickets,
            ),
            "get_technician": AgentTool(
                name="get_technician",
                description="Get one technician with qualifications and assignments.",
                input_model=GetTechnicianInput,
                handler=self._get_technician,
            ),
            "search_technicians": AgentTool(
                name="search_technicians",
                description="Search technicians using status and certification filters.",
                input_model=SearchTechniciansInput,
                handler=self._search_technicians,
            ),
            "recommend_assignment": AgentTool(
                name="recommend_assignment",
                description=(
                    "Rank eligible technicians for a ticket using policy and route evidence."
                ),
                input_model=RecommendAssignmentInput,
                handler=self._recommend_assignment,
            ),
            "search_knowledge": AgentTool(
                name="search_knowledge",
                description="Retrieve cited passages from operational source documents.",
                input_model=SearchKnowledgeInput,
                handler=self._search_knowledge,
            ),
        }

    @property
    def definitions(self) -> list[AgentTool[Any]]:
        return list(self._tools.values())

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        trace_id: str,
        session_id: str,
        agent_run_id: str,
    ) -> tuple[ToolOutput, AgentToolUse]:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolExecutionError(f"Unknown tool: {name}")
        started = perf_counter()
        try:
            validated = tool.input_model.model_validate(arguments)
            output = await tool.handler(validated)
        except ValidationError as exc:
            raise ToolExecutionError(f"Invalid {name} arguments") from exc
        latency_ms = round((perf_counter() - started) * 1_000, 2)
        evidence = AgentToolUse(
            tool=name,
            status="success",
            latency_ms=latency_ms,
            summary=output.summary,
            retrieval_count=output.retrieval_count,
        )
        logger.info(
            "agent_tool_completed",
            extra={
                "trace_id": trace_id,
                "session_id": session_id,
                "agent_run_id": agent_run_id,
                "tool": name,
                "latency_ms": latency_ms,
                "retrieval_count": output.retrieval_count,
                "success": True,
            },
        )
        return output, evidence

    async def _get_ticket(self, payload: GetTicketInput) -> ToolOutput:
        ticket = await self._catalog.get_ticket(payload.ticket_id)
        return ToolOutput(
            data={"ticket": ticket.model_dump(mode="json") if ticket else None},
            summary=(
                f"Loaded ticket {payload.ticket_id}."
                if ticket
                else f"Ticket {payload.ticket_id} was not found."
            ),
        )

    async def _search_tickets(self, payload: SearchTicketsInput) -> ToolOutput:
        result = await self._catalog.list_tickets(
            status=payload.status,
            priority=payload.priority,
            query=payload.query,
            limit=payload.limit,
            offset=0,
        )
        return ToolOutput(
            data=result.model_dump(mode="json"),
            summary=f"Found {result.total} matching tickets; returned {len(result.items)}.",
            retrieval_count=len(result.items),
        )

    async def _get_technician(self, payload: GetTechnicianInput) -> ToolOutput:
        technician = await self._catalog.get_technician(payload.technician_id)
        return ToolOutput(
            data={
                "technician": technician.model_dump(mode="json") if technician else None
            },
            summary=(
                f"Loaded technician {payload.technician_id}."
                if technician
                else f"Technician {payload.technician_id} was not found."
            ),
        )

    async def _search_technicians(
        self, payload: SearchTechniciansInput
    ) -> ToolOutput:
        result = await self._catalog.list_technicians(
            status=payload.status,
            certification_id=payload.certification_id,
            query=payload.query,
            limit=payload.limit,
            offset=0,
        )
        return ToolOutput(
            data=result.model_dump(mode="json"),
            summary=(
                f"Found {result.total} matching technicians; returned {len(result.items)}."
            ),
            retrieval_count=len(result.items),
        )

    async def _recommend_assignment(
        self, payload: RecommendAssignmentInput
    ) -> ToolOutput:
        result = await self._dispatch.recommend(payload.ticket_id)
        candidate = result.eligible_candidates[0] if result and result.eligible_candidates else None
        summary = (
            f"Recommended {candidate.technician_name} for ticket {payload.ticket_id}."
            if candidate
            else f"No eligible technician was found for ticket {payload.ticket_id}."
        )
        return ToolOutput(
            data={"recommendation": result.model_dump(mode="json") if result else None},
            summary=summary,
            retrieval_count=len(result.eligible_candidates) if result else 0,
        )

    async def _search_knowledge(self, payload: SearchKnowledgeInput) -> ToolOutput:
        hits = await self._knowledge.search(
            payload.query,
            filters=KnowledgeFilters(
                customer_id=payload.customer_id,
                equipment_type=payload.equipment_type,
                document_type=payload.document_type,
            ),
            limit=payload.limit,
            minimum_score=0.05,
        )
        sources = [
            KnowledgeSource(
                rank=rank,
                score=hit.score,
                citation=hit.citation,
                chunk_id=hit.chunk.chunk_id,
                document_id=hit.chunk.document_id,
                title=hit.chunk.title,
                document_type=hit.chunk.document_type,
                version=hit.chunk.version,
                effective_date=hit.chunk.effective_date,
                customer_id=hit.chunk.customer_id,
                equipment_type=hit.chunk.equipment_type,
                section=hit.chunk.section,
                excerpt=hit.chunk.text,
                storage_uri=hit.chunk.storage_uri,
            )
            for rank, hit in enumerate(hits, 1)
        ]
        return ToolOutput(
            data={"sources": [item.model_dump(mode="json") for item in sources]},
            summary=f"Retrieved {len(sources)} cited source passages.",
            sources=sources,
            retrieval_count=len(sources),
        )
