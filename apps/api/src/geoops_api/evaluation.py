"""Reproducible agent evaluations with explicit labels and configurable gates."""

import argparse
import asyncio
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from geoops_api.config import Settings
from geoops_api.schemas.agent import ChatRequest, ChatResponse
from geoops_api.state import DocumentStore

DATA_ROOT = Path(__file__).resolve().parents[4] / "data/evaluation"


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    prompt: str
    expected_tools: list[str]
    expected_arguments: dict[str, dict[str, Any]] = Field(default_factory=dict)
    expected_facts: list[str] = Field(default_factory=list)
    expected_document_ids: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    proposal_expected: bool = False


class EvaluationResult(BaseModel):
    case_id: str
    task_success: bool
    tool_selection_accuracy: float
    tool_argument_accuracy: float | None
    retrieval_recall: float | None
    citation_correctness: float | None
    policy_compliance: float
    approval_correctness: float
    latency_ms: float
    token_usage: int | None
    estimated_cost_usd: float | None
    error_type: str | None = None


class EvaluationRun(BaseModel):
    run_id: str
    created_at: datetime
    provider: str
    model: str
    dataset_sha256: str
    thresholds: dict[str, float]
    metrics: dict[str, float | None]
    passed: bool
    results: list[EvaluationResult]


def score_case(case: EvaluationCase, response: ChatResponse, latency_ms: float) -> EvaluationResult:
    actual = {item.tool for item in response.tools_used}
    expected = set(case.expected_tools)
    tool_score = len(actual & expected) / len(actual | expected) if actual | expected else 1.0
    argument_checks = [
        any(
            item.tool == tool
            and all(item.arguments.get(key) == value for key, value in labels.items())
            for item in response.tools_used
        )
        for tool, labels in case.expected_arguments.items()
    ]
    documents = {item.document_id for item in response.sources}
    recall = (
        len(documents & set(case.expected_document_ids)) / len(case.expected_document_ids)
        if case.expected_document_ids
        else None
    )
    citations = (
        mean(
            float(bool(item.citation and item.excerpt and item.document_id))
            for item in response.sources
        )
        if response.sources
        else None
    )
    policy = float(not (set(case.forbidden_actions) & actual))
    has_proposal = bool(response.recommended_action and response.recommended_action.approval_id)
    approval = float(
        response.requires_approval == case.requires_approval
        and has_proposal == case.proposal_expected
    )
    facts = all(fact.casefold() in response.answer.casefold() for fact in case.expected_facts)
    arguments = mean(argument_checks) if argument_checks else None
    return EvaluationResult(
        case_id=case.id,
        task_success=(
            tool_score == 1
            and facts
            and policy == 1
            and approval == 1
            and arguments in (None, 1)
            and recall in (None, 1)
        ),
        tool_selection_accuracy=tool_score,
        tool_argument_accuracy=arguments,
        retrieval_recall=recall,
        citation_correctness=citations,
        policy_compliance=policy,
        approval_correctness=approval,
        latency_ms=latency_ms,
        token_usage=(
            response.tokens_in + response.tokens_out
            if response.tokens_in is not None and response.tokens_out is not None
            else None
        ),
        estimated_cost_usd=response.estimated_cost_usd,
    )


def summarize(results: list[EvaluationResult]) -> dict[str, float | None]:
    metrics: dict[str, float | None] = {}
    for name in (
        "task_success",
        "tool_selection_accuracy",
        "tool_argument_accuracy",
        "retrieval_recall",
        "citation_correctness",
        "policy_compliance",
        "approval_correctness",
        "token_usage",
        "estimated_cost_usd",
    ):
        values = [float(value) for item in results if (value := getattr(item, name)) is not None]
        metrics[name] = mean(values) if values else None
    latencies = sorted(item.latency_ms for item in results)
    for percentile in (50, 95):
        metrics[f"p{percentile}_latency_ms"] = (
            latencies[max(0, math.ceil(len(latencies) * percentile / 100) - 1)]
            if latencies
            else None
        )
    successful = sum(item.task_success for item in results)
    known_costs = [
        item.estimated_cost_usd for item in results if item.estimated_cost_usd is not None
    ]
    metrics["cost_per_success_usd"] = (
        sum(known_costs) / successful if successful and len(known_costs) == len(results) else None
    )
    return metrics


class EvaluationService:
    def __init__(self, settings: Settings, store: DocumentStore) -> None:
        self.settings = settings
        self.store = store
        self._lock = asyncio.Lock()

    async def list_runs(self) -> list[EvaluationRun]:
        runs = [EvaluationRun.model_validate(item) for item in await self.store.scan("evaluations")]
        return sorted(runs, key=lambda run: run.created_at, reverse=True)

    async def run(self) -> EvaluationRun:
        from geoops_api.container import build_container

        async with self._lock:
            raw = self.settings.evaluation_dataset_path.read_bytes()
            cases = [EvaluationCase.model_validate(item) for item in json.loads(raw)]
            if not cases or len({case.id for case in cases}) != len(cases):
                raise ValueError("Evaluation cases must be nonempty with unique IDs")
            thresholds: dict[str, float] = json.loads(
                self.settings.evaluation_thresholds_path.read_text()
            )
            results: list[EvaluationResult] = []
            for case in cases:
                isolated_settings = self.settings.model_copy(
                    update={
                        "approval_store": "memory",
                        "event_bus": "memory",
                        "worker_enabled": False,
                        "analytics_provider": "local",
                        "document_provider": "local",
                        "vector_provider": "memory",
                        "catalog_provider": "json",
                        "embedding_provider": "local",
                    }
                )
                isolated = build_container(isolated_settings)
                started = perf_counter()
                try:
                    response = await asyncio.wait_for(
                        isolated.agent_runtime.run(
                            ChatRequest(message=case.prompt), trace_id=f"eval-{case.id}"
                        ),
                        timeout=self.settings.agent_timeout_seconds,
                    )
                    result = score_case(case, response, (perf_counter() - started) * 1000)
                except Exception as exc:
                    result = EvaluationResult(
                        case_id=case.id,
                        task_success=False,
                        tool_selection_accuracy=0,
                        tool_argument_accuracy=None,
                        retrieval_recall=None,
                        citation_correctness=None,
                        policy_compliance=0,
                        approval_correctness=0,
                        latency_ms=(perf_counter() - started) * 1000,
                        token_usage=None,
                        estimated_cost_usd=None,
                        error_type=type(exc).__name__,
                    )
                finally:
                    await isolated.event_bus.close()
                    await isolated.approval_repository.store.close()
                results.append(result)
            metrics = summarize(results)
            for metric, threshold in thresholds.items():
                if metric not in metrics or not 0 <= threshold <= 1:
                    raise ValueError(f"Invalid evaluation threshold: {metric}")
            run = EvaluationRun(
                run_id=f"eval-{uuid4().hex}",
                created_at=datetime.now(UTC),
                provider=self.settings.model_provider,
                model=self.settings.model_name,
                dataset_sha256=hashlib.sha256(raw).hexdigest(),
                thresholds=thresholds,
                metrics=metrics,
                passed=all(
                    metrics[key] is not None and float(metrics[key] or 0) >= value
                    for key, value in thresholds.items()
                ),
                results=results,
            )
            await self.store.transact(
                [], lambda _: {f"evaluations/{run.run_id}": run.model_dump(mode="json")}
            )
            return run


async def cli() -> int:
    parser = argparse.ArgumentParser(description="Run the configured agent regression suite")
    parser.add_argument(
        "--local", action="store_true", help="Force key-free deterministic providers"
    )
    args = parser.parse_args()
    settings = Settings()
    if args.local:
        settings = settings.model_copy(
            update={
                "model_provider": "local",
                "maps_provider": "mock",
                "model_name": "geoops-local-planner-v1",
            }
        )
    from geoops_api.container import build_container

    container = build_container(settings)
    try:
        run = await container.evaluation_service.run()
        print(run.model_dump_json(indent=2))
        return 0 if run.passed else 1
    finally:
        await container.event_bus.close()
        await container.approval_repository.store.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(cli()))
