"""Application boundaries, persisted telemetry, and failure contracts."""

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from geoops_api.config import Settings
from geoops_api.container import build_container
from geoops_api.main import create_app


def test_service_auth_protects_operations_and_keeps_health_available() -> None:
    with TestClient(create_app(Settings(_env_file=None, api_token="test-service-token"))) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/operations").status_code == 401
        response = client.get("/api/operations", headers={"X-Geoops-Token": "test-service-token"})
        assert response.status_code == 200
        assert response.json()["active_tickets"] > 0
    with pytest.raises(ValidationError, match="API_TOKEN"):
        Settings(_env_file=None, app_env="production")


def test_chat_records_run_and_reuses_ticket_context() -> None:
    with TestClient(create_app(Settings(_env_file=None))) as client:
        first = client.post("/api/chat", json={"message": "Show ticket 184"}).json()
        second = client.post(
            "/api/chat",
            json={
                "message": "Who is the best technician for it?",
                "session_id": first["session_id"],
            },
        ).json()
        assert "James Chen" in second["answer"]
        summary = client.get("/api/operations").json()
        assert len(summary["recent_agent_runs"]) == 2


def test_agent_timeout_returns_504_instead_of_inventing_an_answer() -> None:
    settings = Settings(_env_file=None)
    container = build_container(settings)

    class TimedOutRuntime:
        async def run(self, *args, **kwargs):
            raise TimeoutError("provider timed out")

    with TestClient(
        create_app(settings, replace(container, agent_runtime=TimedOutRuntime()))
    ) as client:
        response = client.post("/api/chat", json={"message": "Show ticket 184"})
        assert response.status_code == 504
        assert response.json()["detail"] == "Agent request timed out"
