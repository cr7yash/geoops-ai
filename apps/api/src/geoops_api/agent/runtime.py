"""Provider-neutral agent runtimes and the deterministic local implementation."""

import logging
import re
from typing import Protocol
from uuid import uuid4

from geoops_api.agent.tools import AgentToolRegistry, ToolOutput
from geoops_api.domain.models import TechnicianStatus, TicketPriority, TicketStatus
from geoops_api.schemas.agent import (
    AgentToolUse,
    ChatRequest,
    ChatResponse,
    RecommendedAction,
)
from geoops_api.schemas.knowledge import KnowledgeSource

logger = logging.getLogger("geoops.agent.runtime")


def requests_mutation(message: str) -> bool:
    """Conservatively identify writes that Phase 6 must never attempt."""
    normalized = message.lower()
    return any(
        token in normalized
        for token in (
            "assign ",
            "reassign",
            "dispatch ",
            "cancel ticket",
            "close ticket",
            "update ticket",
        )
    )


class AgentRuntime(Protocol):
    async def run(self, request: ChatRequest, *, trace_id: str) -> ChatResponse: ...


class LocalAgentRuntime:
    """Deterministic planner used for key-free development and tests."""

    def __init__(self, registry: AgentToolRegistry, *, model_name: str) -> None:
        self._registry = registry
        self._model_name = model_name

    async def run(self, request: ChatRequest, *, trace_id: str) -> ChatResponse:
        session_id = request.session_id or f"session-{uuid4().hex}"
        agent_run_id = f"run-{uuid4().hex}"
        message = request.message.strip()
        normalized = message.lower()
        tools_used: list[AgentToolUse] = []

        if requests_mutation(normalized):
            return self._response(
                answer=(
                    "I can inspect operational data and prepare recommendations, but I "
                    "cannot change an assignment in Phase 6. This action requires the "
                    "approval workflow introduced in Phase 7."
                ),
                trace_id=trace_id,
                session_id=session_id,
                agent_run_id=agent_run_id,
                tools_used=tools_used,
                confidence=1.0,
                requires_approval=True,
            )

        ticket_id = self._ticket_id(message)
        if ticket_id and self._is_dispatch_question(normalized):
            ticket_output = await self._call(
                "get_ticket",
                {"ticket_id": ticket_id},
                trace_id,
                session_id,
                agent_run_id,
                tools_used,
            )
            ticket = ticket_output.data["ticket"]
            if ticket is None:
                return self._response(
                    answer=f"Ticket {ticket_id} was not found.",
                    trace_id=trace_id,
                    session_id=session_id,
                    agent_run_id=agent_run_id,
                    tools_used=tools_used,
                    confidence=1.0,
                )
            recommendation_output = await self._call(
                "recommend_assignment",
                {"ticket_id": ticket_id},
                trace_id,
                session_id,
                agent_run_id,
                tools_used,
            )
            recommendation = recommendation_output.data["recommendation"]
            candidates = recommendation["eligible_candidates"] if recommendation else []
            if not candidates:
                return self._response(
                    answer=(
                        f"No technician currently passes every eligibility gate for ticket "
                        f"{ticket_id}. Review the recorded exclusion reasons before changing "
                        "coverage or qualification rules."
                    ),
                    trace_id=trace_id,
                    session_id=session_id,
                    agent_run_id=agent_run_id,
                    tools_used=tools_used,
                    confidence=0.98,
                )
            top = candidates[0]
            distance = top["distance_km"]
            duration = top["travel_duration_minutes"]
            route_label = "estimated route" if top["route_is_estimate"] else "route"
            return self._response(
                answer=(
                    f"{top['technician_name']} is the highest-ranked eligible technician "
                    f"for ticket {ticket_id}, with a score of {top['score']:.2f}. The "
                    f"{route_label} is {distance:.1f} km and {duration:.1f} minutes. "
                    f"The recommendation is read-only; no assignment was changed."
                ),
                trace_id=trace_id,
                session_id=session_id,
                agent_run_id=agent_run_id,
                tools_used=tools_used,
                confidence=0.99,
                recommended_action=RecommendedAction(
                    kind="review_dispatch_recommendation",
                    label=f"Review {top['technician_name']} for ticket {ticket_id}",
                    ticket_id=ticket_id,
                    technician_id=top["technician_id"],
                ),
            )

        if self._is_knowledge_question(normalized):
            filters: dict[str, object] = {"query": message, "limit": 5}
            if ticket_id:
                ticket_output = await self._call(
                    "get_ticket",
                    {"ticket_id": ticket_id},
                    trace_id,
                    session_id,
                    agent_run_id,
                    tools_used,
                )
                ticket = ticket_output.data["ticket"]
                if ticket:
                    filters["customer_id"] = ticket["customer_id"]
                    filters["equipment_type"] = ticket["equipment_type"]
            knowledge = await self._call(
                "search_knowledge",
                filters,
                trace_id,
                session_id,
                agent_run_id,
                tools_used,
            )
            if not knowledge.sources:
                return self._response(
                    answer="No cited source passage matched this question.",
                    trace_id=trace_id,
                    session_id=session_id,
                    agent_run_id=agent_run_id,
                    tools_used=tools_used,
                    confidence=0.3,
                )
            lead = knowledge.sources[0]
            return self._response(
                answer=(
                    f"The strongest source is {lead.title}, section “{lead.section}”. "
                    f"It says: {lead.excerpt}"
                ),
                trace_id=trace_id,
                session_id=session_id,
                agent_run_id=agent_run_id,
                tools_used=tools_used,
                confidence=max(0.5, min(0.98, lead.score)),
                sources=knowledge.sources,
            )

        if ticket_id:
            output = await self._call(
                "get_ticket",
                {"ticket_id": ticket_id},
                trace_id,
                session_id,
                agent_run_id,
                tools_used,
            )
            ticket = output.data["ticket"]
            answer = (
                f"Ticket {ticket_id}: {ticket['title']}. Status is "
                f"{ticket['status'].replace('_', ' ')}, priority is {ticket['priority']}, "
                f"and SLA state is {ticket['sla_state'].replace('_', ' ')}."
                if ticket
                else f"Ticket {ticket_id} was not found."
            )
            return self._response(
                answer=answer,
                trace_id=trace_id,
                session_id=session_id,
                agent_run_id=agent_run_id,
                tools_used=tools_used,
                confidence=1.0,
            )

        if "technician" in normalized or "tech" in normalized:
            arguments: dict[str, object] = {"limit": 10}
            if "available" in normalized:
                arguments["status"] = TechnicianStatus.AVAILABLE
            output = await self._call(
                "search_technicians",
                arguments,
                trace_id,
                session_id,
                agent_run_id,
                tools_used,
            )
            items = output.data["items"]
            names = ", ".join(item["name"] for item in items[:5])
            return self._response(
                answer=(
                    f"Found {output.data['total']} matching technicians. "
                    f"The first results are: {names}."
                ),
                trace_id=trace_id,
                session_id=session_id,
                agent_run_id=agent_run_id,
                tools_used=tools_used,
                confidence=1.0,
            )

        if any(token in normalized for token in ("ticket", "sla", "overdue")):
            arguments = {"limit": 10}
            status = self._ticket_status(normalized)
            priority = self._ticket_priority(normalized)
            if status:
                arguments["status"] = status
            if priority:
                arguments["priority"] = priority
            output = await self._call(
                "search_tickets",
                arguments,
                trace_id,
                session_id,
                agent_run_id,
                tools_used,
            )
            items = output.data["items"]
            descriptions = ", ".join(
                f"{item['ticket_id']} ({item['sla_state'].replace('_', ' ')})"
                for item in items[:5]
            )
            return self._response(
                answer=(
                    f"Found {output.data['total']} matching tickets. "
                    f"The first results are: {descriptions}."
                ),
                trace_id=trace_id,
                session_id=session_id,
                agent_run_id=agent_run_id,
                tools_used=tools_used,
                confidence=1.0,
            )

        return self._response(
            answer=(
                "I can inspect tickets and technicians, rank eligible technicians for a "
                "ticket, and retrieve cited operational knowledge. Include a ticket ID "
                "when you want a ticket-specific answer."
            ),
            trace_id=trace_id,
            session_id=session_id,
            agent_run_id=agent_run_id,
            tools_used=tools_used,
            confidence=1.0,
        )

    async def _call(
        self,
        name: str,
        arguments: dict[str, object],
        trace_id: str,
        session_id: str,
        agent_run_id: str,
        tools_used: list[AgentToolUse],
    ) -> ToolOutput:
        output, evidence = await self._registry.execute(
            name,
            arguments,
            trace_id=trace_id,
            session_id=session_id,
            agent_run_id=agent_run_id,
        )
        tools_used.append(evidence)
        return output

    def _response(
        self,
        *,
        answer: str,
        trace_id: str,
        session_id: str,
        agent_run_id: str,
        tools_used: list[AgentToolUse],
        confidence: float,
        requires_approval: bool = False,
        recommended_action: RecommendedAction | None = None,
        sources: list[KnowledgeSource] | None = None,
    ) -> ChatResponse:
        return ChatResponse(
            answer=answer,
            recommended_action=recommended_action,
            sources=sources or [],
            tools_used=tools_used,
            confidence=confidence,
            requires_approval=requires_approval,
            trace_id=trace_id,
            session_id=session_id,
            agent_run_id=agent_run_id,
            model_provider="local",
            model_name=self._model_name,
        )

    @staticmethod
    def _ticket_id(message: str) -> str | None:
        match = re.search(r"\b(?:ticket\s*#?\s*)?(\d{3,})\b", message, re.IGNORECASE)
        return match.group(1) if match else None

    @staticmethod
    def _is_dispatch_question(message: str) -> bool:
        return any(
            token in message
            for token in ("recommend", "best technician", "who should", "qualified")
        )

    @staticmethod
    def _is_knowledge_question(message: str) -> bool:
        return any(
            token in message
            for token in (
                "manual",
                "contract",
                "policy",
                "procedure",
                "service history",
                "incident",
                "troubleshoot",
                "what should be checked",
            )
        )

    @staticmethod
    def _ticket_status(message: str) -> TicketStatus | None:
        return next((status for status in TicketStatus if status.value in message), None)

    @staticmethod
    def _ticket_priority(message: str) -> TicketPriority | None:
        return next((priority for priority in TicketPriority if priority.value in message), None)
