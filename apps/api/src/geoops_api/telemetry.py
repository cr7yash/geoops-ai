"""Agent telemetry, bounded session context, and retryable analytical export."""

import asyncio
import logging
import re
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import uuid4

from geoops_api.agent.runtime import AgentRuntime
from geoops_api.analytics import AnalyticsStore
from geoops_api.schemas.agent import ChatRequest, ChatResponse
from geoops_api.state import DocumentStore

logger = logging.getLogger("geoops.agent")


class RecordedAgentRuntime:
    def __init__(
        self,
        runtime: AgentRuntime,
        store: DocumentStore,
        timeout: float,
        input_price: float | None = None,
        output_price: float | None = None,
    ) -> None:
        self.runtime = runtime
        self.store = store
        self.timeout = timeout
        self.input_price = input_price
        self.output_price = output_price

    async def run(self, request: ChatRequest, *, trace_id: str) -> ChatResponse:
        started_at = datetime.now(UTC)
        started = perf_counter()
        session_id = request.session_id or f"session-{uuid4().hex}"
        key = f"sessions/{session_id}"
        previous = await self.store.get(key)
        message = request.message
        ticket = re.search(r"\bticket\s*#?\s*(\d+)\b", message, re.IGNORECASE)
        if (
            not ticket
            and previous
            and previous.get("ticket_id")
            and re.search(r"\b(it|this ticket|that ticket)\b", message, re.IGNORECASE)
        ):
            message += f" (ticket {previous['ticket_id']})"
        try:
            response = await asyncio.wait_for(
                self.runtime.run(
                    request.model_copy(update={"message": message, "session_id": session_id}),
                    trace_id=trace_id,
                ),
                timeout=self.timeout,
            )
        except Exception as exc:
            run_id = f"run-{uuid4().hex}"
            failed_record = {
                "agent_run_id": run_id,
                "session_id": session_id,
                "trace_id": trace_id,
                "started_at": started_at.isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
                "status": "failed",
                "model": "unavailable",
                "latency_ms": (perf_counter() - started) * 1000,
                "error_type": type(exc).__name__,
                "success": False,
            }
            await self.store.transact([], lambda _: {f"agent_runs/{run_id}": failed_record})
            logger.error(
                "agent_run_failed",
                extra={
                    "trace_id": trace_id,
                    "session_id": session_id,
                    "error_type": type(exc).__name__,
                    "success": False,
                },
            )
            raise
        elapsed = (perf_counter() - started) * 1000
        if (
            response.tokens_in is not None
            and response.tokens_out is not None
            and self.input_price is not None
            and self.output_price is not None
        ):
            response = response.model_copy(
                update={
                    "estimated_cost_usd": (
                        response.tokens_in * self.input_price
                        + response.tokens_out * self.output_price
                    )
                    / 1_000_000
                }
            )
        record = {
            "agent_run_id": response.agent_run_id,
            "session_id": session_id,
            "trace_id": trace_id,
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
            "status": "completed",
            "model": response.model_name,
            "model_provider": response.model_provider,
            "tool_names": [tool.tool for tool in response.tools_used],
            "latency_ms": elapsed,
            "tokens_in": response.tokens_in,
            "tokens_out": response.tokens_out,
            "success": True,
        }

        def save(documents: dict[str, Any]) -> dict[str, Any]:
            return {
                f"agent_runs/{response.agent_run_id}": record,
                key: {
                    "session_id": session_id,
                    "last_run_id": response.agent_run_id,
                    "ticket_id": ticket.group(1) if ticket else (previous or {}).get("ticket_id"),
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            }

        await self.store.transact([key], save)
        logger.info("agent_run_completed", extra=record)
        return response


class AnalyticsRelay:
    def __init__(self, store: DocumentStore, analytics: AnalyticsStore) -> None:
        self.store = store
        self.analytics = analytics

    async def run_once(self) -> int:
        count = 0
        for collection, identifier in (
            ("history", "event_id"),
            ("evaluations", "run_id"),
            ("agent_runs", "agent_run_id"),
        ):
            for record in await self.store.scan(collection):
                record_id = str(record[identifier])
                key = f"exports/{collection}-{record_id}"
                if await self.store.get(key):
                    continue
                await self.analytics.save(collection, record_id, record)

                def mark_exported(_: dict[str, Any], export_key: str = key) -> dict[str, Any]:
                    return {export_key: {"exported": True}}

                await self.store.transact([], mark_exported)
                count += 1
        return count
