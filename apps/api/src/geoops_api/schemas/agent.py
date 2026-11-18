"""Public contracts for safe agent orchestration."""

from typing import Literal

from pydantic import Field

from geoops_api.schemas.catalog import ApiModel
from geoops_api.schemas.knowledge import KnowledgeSource


class ChatRequest(ApiModel):
    message: str = Field(min_length=2, max_length=2_000)
    session_id: str | None = Field(default=None, min_length=8, max_length=100)


class AgentToolUse(ApiModel):
    tool: str
    status: Literal["success", "error"]
    latency_ms: float = Field(ge=0)
    summary: str
    retrieval_count: int | None = Field(default=None, ge=0)


class RecommendedAction(ApiModel):
    kind: Literal["review_dispatch_recommendation", "review_approval_request"]
    label: str
    ticket_id: str
    technician_id: str | None = None
    approval_id: str | None = None


class ChatResponse(ApiModel):
    answer: str
    recommended_action: RecommendedAction | None = None
    sources: list[KnowledgeSource] = Field(default_factory=list)
    tools_used: list[AgentToolUse] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    requires_approval: bool
    trace_id: str
    session_id: str
    agent_run_id: str
    model_provider: str
    model_name: str
