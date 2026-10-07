"""Contract and safety tests for Phase 6 agent orchestration."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from geoops_api.config import Settings
from geoops_api.container import build_container
from geoops_api.main import create_app


def make_client() -> TestClient:
    return TestClient(create_app(Settings(_env_file=None)))


def test_chat_recommends_with_tool_and_route_evidence() -> None:
    with make_client() as client:
        response = client.post(
            "/api/chat",
            json={"message": "Who is the best technician for ticket 184?"},
            headers={"X-Request-ID": "agent-trace-184"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert "James Chen" in payload["answer"]
    assert "no assignment was changed" in payload["answer"].lower()
    assert payload["recommended_action"] == {
        "kind": "review_dispatch_recommendation",
        "label": "Review James Chen for ticket 184",
        "ticket_id": "184",
        "technician_id": "T-001",
        "approval_id": None,
    }
    assert [item["tool"] for item in payload["tools_used"]] == [
        "get_ticket",
        "recommend_assignment",
    ]
    assert payload["requires_approval"] is False
    assert payload["trace_id"] == "agent-trace-184"
    assert payload["model_provider"] == "local"


def test_chat_retrieves_cited_knowledge_for_ticket() -> None:
    with make_client() as client:
        response = client.post(
            "/api/chat",
            json={"message": "What procedure should I use to troubleshoot ticket 184?"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sources"]
    assert (
        payload["sources"][0]["citation"] in payload["answer"]
        or payload["sources"][0]["title"] in payload["answer"]
    )
    assert [item["tool"] for item in payload["tools_used"]] == [
        "get_ticket",
        "search_knowledge",
    ]


def test_chat_creates_a_validated_approval_without_mutating_assignment() -> None:
    with make_client() as client:
        response = client.post(
            "/api/chat",
            json={"message": "Reassign ticket 184 to James Chen"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["requires_approval"] is True
    assert payload["recommended_action"]["kind"] == "review_approval_request"
    assert payload["recommended_action"]["approval_id"].startswith("APR-")
    assert [item["tool"] for item in payload["tools_used"]] == [
        "search_technicians",
        "request_dispatch_approval",
    ]
    assert "pending human review" in payload["answer"]
    assert "no assignment has been changed" in payload["answer"]


def test_chat_supports_session_continuity_identifier() -> None:
    with make_client() as client:
        response = client.post(
            "/api/chat",
            json={
                "message": "Show ticket 184",
                "session_id": "session-test-184",
            },
        )

    assert response.status_code == 200
    assert response.json()["session_id"] == "session-test-184"


def test_chat_validates_request_contract() -> None:
    with make_client() as client:
        response = client.post("/api/chat", json={"message": "x"})

    assert response.status_code == 422


def test_model_provider_configuration_requires_credentials() -> None:
    with pytest.raises(ValidationError, match="GEMINI_API_KEY"):
        Settings(_env_file=None, model_provider="gemini_api")
    with pytest.raises(ValidationError, match="GOOGLE_CLOUD_PROJECT"):
        Settings(_env_file=None, model_provider="vertex_ai")

    gemini = Settings(
        _env_file=None,
        model_provider="gemini_api",
        gemini_api_key="test-key",
    )
    vertex = Settings(
        _env_file=None,
        model_provider="vertex_ai",
        google_cloud_project="test-project",
    )
    assert gemini.model_provider == "gemini_api"
    assert vertex.google_cloud_location == "us-central1"


def test_google_adk_runtime_is_selected_without_exposing_credentials() -> None:
    settings = Settings(
        _env_file=None,
        model_provider="gemini_api",
        model_name="gemini-test-model",
        gemini_api_key="secret-test-key",
    )
    runtime = build_container(settings).agent_runtime

    assert runtime.__class__.__name__ == "GoogleAdkRuntime"
    assert runtime.describe() == (  # type: ignore[attr-defined]
        '{"model": "gemini-test-model", "provider": "gemini_api"}'
    )
    assert "secret-test-key" not in runtime.describe()  # type: ignore[attr-defined]


def test_google_adk_runtime_routes_mutations_through_local_approval_policy() -> None:
    settings = Settings(
        _env_file=None,
        model_provider="gemini_api",
        model_name="gemini-test-model",
        gemini_api_key="secret-test-key",
    )
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/chat",
            json={"message": "Assign ticket 184 to technician T-001"},
        )

    assert response.status_code == 200
    assert response.json()["requires_approval"] is True
    assert response.json()["recommended_action"]["approval_id"].startswith("APR-")
    assert response.json()["model_provider"] == "local-policy"
