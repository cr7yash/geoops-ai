"""API contracts for provider-neutral geocoding and routing."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from geoops_api.config import Settings
from geoops_api.main import create_app


def make_client() -> TestClient:
    return TestClient(create_app(Settings(_env_file=None)))


def test_mock_geocoding_uses_seed_site_addresses() -> None:
    with make_client() as client:
        response = client.post(
            "/api/maps/geocode",
            json={"address": "42 Signal Way, Mountain View, CA 94043"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "provider": "mock",
        "formatted_address": "42 Signal Way, Mountain View, CA 94043",
        "location": {"latitude": 37.414, "longitude": -122.078},
        "place_id": "mock:S-023",
        "precision": "seed",
    }


def test_unknown_mock_geocode_returns_not_found() -> None:
    with make_client() as client:
        response = client.post(
            "/api/maps/geocode",
            json={"address": "999 Missing Place, Nowhere, CA 99999"},
        )

    assert response.status_code == 404
    assert "No deterministic geocode exists" in response.json()["detail"]


def test_mock_route_and_matrix_are_deterministic() -> None:
    route_payload = {
        "origin": {"latitude": 37.7749, "longitude": -122.4194},
        "destination": {"latitude": 37.8044, "longitude": -122.2712},
        "departure_time": "2026-10-06T09:00:00Z",
    }
    matrix_payload = {
        "origins": [
            {
                "waypoint_id": "origin-1",
                "location": route_payload["origin"],
            }
        ],
        "destinations": [
            {
                "waypoint_id": "destination-1",
                "location": route_payload["destination"],
            }
        ],
        "departure_time": route_payload["departure_time"],
    }

    with make_client() as client:
        first = client.post("/api/maps/routes", json=route_payload)
        second = client.post("/api/maps/routes", json=route_payload)
        matrix = client.post("/api/maps/route-matrix", json=matrix_payload)

    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["provider"] == "mock"
    assert first.json()["status"] == "ok"
    assert first.json()["is_estimate"] is True
    assert first.json()["duration_minutes"] > 0
    assert matrix.status_code == 200
    assert matrix.json()["elements"] == [
        {
            "origin_id": "origin-1",
            "destination_id": "destination-1",
            "status": "ok",
            "distance_km": first.json()["distance_km"],
            "duration_minutes": first.json()["duration_minutes"],
            "error_message": None,
        }
    ]


def test_simulated_route_failure_is_an_explicit_bad_gateway() -> None:
    with make_client() as client:
        response = client.post(
            "/api/maps/routes",
            json={
                "origin": {"latitude": 37.7749, "longitude": -122.4194},
                "destination": {"latitude": 37.414, "longitude": -122.078},
            },
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "Maps provider could not compute the route"}


def test_google_provider_requires_a_nonempty_api_key() -> None:
    with pytest.raises(ValidationError, match="GOOGLE_MAPS_API_KEY is required"):
        Settings(_env_file=None, maps_provider="google")

    with pytest.raises(ValidationError, match="GOOGLE_MAPS_API_KEY is required"):
        Settings(_env_file=None, maps_provider="google", google_maps_api_key="   ")

    settings = Settings(
        _env_file=None,
        maps_provider="google",
        google_maps_api_key="test-secret",
    )
    assert settings.google_maps_api_key is not None
    assert settings.google_maps_api_key.get_secret_value() == "test-secret"
    assert "test-secret" not in repr(settings)
