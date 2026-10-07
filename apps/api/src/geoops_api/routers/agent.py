"""Read-only operations-agent endpoint."""

from fastapi import APIRouter, Request

from geoops_api.container import ApplicationContainer
from geoops_api.schemas.agent import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["agent"])


@router.post("", response_model=ChatResponse, summary="Ask the operations agent")
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    container: ApplicationContainer = request.app.state.container
    return await container.agent_runtime.run(
        payload,
        trace_id=request.state.request_id,
    )
