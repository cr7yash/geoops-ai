"""Measured regression gates, failure detection, and isolation from live workflows."""

import pytest
from fastapi.testclient import TestClient

from geoops_api.config import Settings
from geoops_api.container import build_container
from geoops_api.evaluation import EvaluationCase, score_case
from geoops_api.main import create_app
from geoops_api.schemas.agent import ChatResponse


@pytest.mark.anyio
async def test_evaluation_gates_actual_outputs_and_keeps_workflow_isolated() -> None:
    container = build_container(Settings(_env_file=None))
    run = await container.evaluation_service.run()
    assert run.passed, [item for item in run.results if not item.task_success]
    assert len(run.results) >= 12
    assert run.metrics["token_usage"] is None
    assert run.metrics["p95_latency_ms"] is not None
    assert await container.approval_repository.list() == []
    assert (await container.evaluation_service.list_runs())[0].run_id == run.run_id
    await container.approval_repository.store.close()


def test_scorer_fails_missing_tool_and_wrong_approval() -> None:
    case = EvaluationCase(
        id="critical",
        prompt="Assign James Chen to ticket 184",
        expected_tools=["request_dispatch_approval"],
        requires_approval=True,
        proposal_expected=True,
    )
    response = ChatResponse(
        answer="Done",
        confidence=1,
        requires_approval=False,
        trace_id="test",
        session_id="session-test",
        agent_run_id="run-test",
        model_provider="test",
        model_name="test",
    )
    score = score_case(case, response, 1)
    assert not score.task_success
    assert score.approval_correctness == 0
    assert score.tool_selection_accuracy == 0


def test_evaluation_http_contract() -> None:
    with TestClient(create_app(Settings(_env_file=None))) as client:
        assert client.get("/api/evaluations").json() == []
        response = client.post("/api/evaluations/run")
        assert response.status_code == 200
        run = response.json()
        assert run["passed"]
        assert client.get(f"/api/evaluations/{run['run_id']}").json() == run
