"""Tests for API configuration and the Phase 1 health contract."""

from fastapi.testclient import TestClient

from geoops_api.config import Settings
from geoops_api.main import create_app


def make_client(**overrides: object) -> TestClient:
    settings = Settings(_env_file=None, **overrides)  # type: ignore[arg-type]
    return TestClient(create_app(settings))


def test_health_returns_deterministic_contract() -> None:
    with make_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "geoops-api",
        "environment": "development",
        "version": "0.1.0",
    }


def test_health_reflects_environment_override() -> None:
    with make_client(app_env="test") as client:
        response = client.get("/health")

    assert response.json()["environment"] == "test"


def test_cors_preflight_allows_configured_frontend() -> None:
    origin = "https://console.example.test"
    with make_client(cors_origins=[origin]) as client:
        response = client.options(
            "/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_request_id_is_preserved_when_supplied() -> None:
    with make_client() as client:
        response = client.get("/health", headers={"X-Request-ID": "trace-test-123"})

    assert response.headers["x-request-id"] == "trace-test-123"


def test_request_id_is_generated_when_missing() -> None:
    with make_client() as client:
        response = client.get("/health")

    assert response.headers["x-request-id"]


def test_unknown_route_returns_404_with_request_id() -> None:
    with make_client() as client:
        response = client.get("/not-a-route")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
    assert response.headers["x-request-id"]
