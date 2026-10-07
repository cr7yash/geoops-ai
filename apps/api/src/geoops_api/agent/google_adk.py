"""Google ADK adapter for Gemini Developer API and Vertex AI."""

import json
from typing import Any
from uuid import uuid4

from google import genai
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.runners import InMemoryRunner
from google.genai import types

from geoops_api.agent.runtime import requests_mutation
from geoops_api.agent.tools import AgentToolRegistry
from geoops_api.schemas.agent import AgentToolUse, ChatRequest, ChatResponse
from geoops_api.schemas.knowledge import KnowledgeSource

SYSTEM_INSTRUCTION = """
You are GeoOps AI, a read-only field-service operations assistant.
Use tools for every operational fact. Never invent tickets, technicians, routes,
eligibility, or source citations. Do not claim that an assignment was changed.
Mutations require a separate human-approval workflow that is not available.
Give concise conclusions and name the evidence that supports them. Never reveal
hidden chain-of-thought or internal reasoning.
""".strip()


class GoogleAdkRuntime:
    """Execute the same typed tool registry through Google's Agent Development Kit."""

    def __init__(
        self,
        registry: AgentToolRegistry,
        *,
        provider: str,
        model_name: str,
        api_key: str | None,
        project: str | None,
        location: str,
    ) -> None:
        self._registry = registry
        self._provider = provider
        self._model_name = model_name
        self._api_key = api_key
        self._project = project
        self._location = location

    async def run(self, request: ChatRequest, *, trace_id: str) -> ChatResponse:
        session_id = request.session_id or f"session-{uuid4().hex}"
        agent_run_id = f"run-{uuid4().hex}"
        evidence: list[AgentToolUse] = []
        sources: list[KnowledgeSource] = []

        if requests_mutation(request.message):
            return ChatResponse(
                answer=(
                    "I can inspect operational data and prepare recommendations, but I "
                    "cannot change an assignment in Phase 6. This action requires the "
                    "approval workflow introduced in Phase 7."
                ),
                tools_used=[],
                confidence=1.0,
                requires_approval=True,
                trace_id=trace_id,
                session_id=session_id,
                agent_run_id=agent_run_id,
                model_provider=self._provider,
                model_name=self._model_name,
            )

        async def get_ticket(ticket_id: str) -> dict[str, Any]:
            """Get a ticket by ID, including site, SLA, and assignments."""
            output, tool_use = await self._registry.execute(
                "get_ticket",
                {"ticket_id": ticket_id},
                trace_id=trace_id,
                session_id=session_id,
                agent_run_id=agent_run_id,
            )
            evidence.append(tool_use)
            return output.data

        async def search_tickets(
            status: str | None = None,
            priority: str | None = None,
            query: str | None = None,
            limit: int = 10,
        ) -> dict[str, Any]:
            """Search tickets by status, priority, or text."""
            arguments = {
                key: value
                for key, value in {
                    "status": status,
                    "priority": priority,
                    "query": query,
                    "limit": limit,
                }.items()
                if value is not None
            }
            output, tool_use = await self._registry.execute(
                "search_tickets",
                arguments,
                trace_id=trace_id,
                session_id=session_id,
                agent_run_id=agent_run_id,
            )
            evidence.append(tool_use)
            return output.data

        async def search_technicians(
            status: str | None = None,
            certification_id: str | None = None,
            query: str | None = None,
            limit: int = 10,
        ) -> dict[str, Any]:
            """Search technicians by availability, certification, or text."""
            arguments = {
                key: value
                for key, value in {
                    "status": status,
                    "certification_id": certification_id,
                    "query": query,
                    "limit": limit,
                }.items()
                if value is not None
            }
            output, tool_use = await self._registry.execute(
                "search_technicians",
                arguments,
                trace_id=trace_id,
                session_id=session_id,
                agent_run_id=agent_run_id,
            )
            evidence.append(tool_use)
            return output.data

        async def get_technician(technician_id: str) -> dict[str, Any]:
            """Get a technician by ID, including qualifications and assignments."""
            output, tool_use = await self._registry.execute(
                "get_technician",
                {"technician_id": technician_id},
                trace_id=trace_id,
                session_id=session_id,
                agent_run_id=agent_run_id,
            )
            evidence.append(tool_use)
            return output.data

        async def recommend_assignment(ticket_id: str) -> dict[str, Any]:
            """Rank eligible technicians for a ticket without assigning anyone."""
            output, tool_use = await self._registry.execute(
                "recommend_assignment",
                {"ticket_id": ticket_id},
                trace_id=trace_id,
                session_id=session_id,
                agent_run_id=agent_run_id,
            )
            evidence.append(tool_use)
            return output.data

        async def search_knowledge(
            query: str,
            customer_id: str | None = None,
            equipment_type: str | None = None,
            document_type: str | None = None,
            limit: int = 5,
        ) -> dict[str, Any]:
            """Retrieve cited operational source passages."""
            arguments = {
                key: value
                for key, value in {
                    "query": query,
                    "customer_id": customer_id,
                    "equipment_type": equipment_type,
                    "document_type": document_type,
                    "limit": limit,
                }.items()
                if value is not None
            }
            output, tool_use = await self._registry.execute(
                "search_knowledge",
                arguments,
                trace_id=trace_id,
                session_id=session_id,
                agent_run_id=agent_run_id,
            )
            evidence.append(tool_use)
            sources.extend(output.sources)
            return output.data

        client = (
            genai.Client(api_key=self._api_key)
            if self._provider == "gemini_api"
            else genai.Client(
                vertexai=True,
                project=self._project,
                location=self._location,
            )
        )
        agent = Agent(
            name="geoops_read_only_agent",
            model=Gemini(model=self._model_name, client=client),
            instruction=SYSTEM_INSTRUCTION,
            tools=[
                get_ticket,
                search_tickets,
                get_technician,
                search_technicians,
                recommend_assignment,
                search_knowledge,
            ],
        )
        runner = InMemoryRunner(app=App(name="geoops", root_agent=agent))
        await runner.session_service.create_session(
            app_name="geoops", user_id="operator", session_id=session_id
        )
        content = types.Content(role="user", parts=[types.Part(text=request.message)])
        answer_parts: list[str] = []
        async for event in runner.run_async(
            user_id="operator", session_id=session_id, new_message=content
        ):
            if event.is_final_response() and event.content:
                answer_parts.extend(
                    part.text for part in event.content.parts or [] if part.text
                )
        answer = "\n".join(answer_parts).strip()
        if not answer:
            answer = "The configured model returned no final response."
        return ChatResponse(
            answer=answer,
            sources=sources,
            tools_used=evidence,
            confidence=0.8,
            requires_approval=False,
            trace_id=trace_id,
            session_id=session_id,
            agent_run_id=agent_run_id,
            model_provider=self._provider,
            model_name=self._model_name,
        )

    def describe(self) -> str:
        """Return a stable diagnostic without exposing credentials."""
        return json.dumps(
            {"provider": self._provider, "model": self._model_name}, sort_keys=True
        )
