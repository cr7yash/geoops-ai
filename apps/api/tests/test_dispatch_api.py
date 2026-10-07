"""Contract tests for deterministic dispatch recommendations."""

from fastapi.testclient import TestClient

from geoops_api.config import Settings
from geoops_api.main import create_app


def make_client() -> TestClient:
    return TestClient(create_app(Settings(_env_file=None)))


def test_recommendation_ranks_only_eligible_candidates() -> None:
    with make_client() as client:
        response = client.get("/api/dispatch/recommendations/184")

    assert response.status_code == 200
    payload = response.json()
    assert payload["policy_version"] == "dispatch-v2-routes"
    assert payload["maps_provider"] == "mock"
    assert payload["maximum_travel_minutes"] == 120.0
    assert payload["total_evaluated"] == 15
    assert payload["recommended_technician_id"] == "T-001"
    assert payload["eligible_candidates"][0]["rank"] == 1
    assert payload["eligible_candidates"][0]["score"] == sum(
        payload["eligible_candidates"][0]["score_breakdown"].values()
    )
    assert payload["eligible_candidates"][0]["route_provider"] == "mock"
    assert payload["eligible_candidates"][0]["route_is_estimate"] is True
    assert payload["eligible_candidates"][0]["travel_duration_minutes"] > 0
    assert "travel_time" in payload["eligible_candidates"][0]["score_breakdown"]
    assert all(candidate["eligible"] for candidate in payload["eligible_candidates"])
    assert all(not candidate["eligible"] for candidate in payload["excluded_candidates"])


def test_recommendation_is_stable_across_calls() -> None:
    with make_client() as client:
        first = client.get("/api/dispatch/recommendations/184").json()
        second = client.get("/api/dispatch/recommendations/184").json()

    assert first == second


def test_no_qualified_technician_is_an_explainable_result() -> None:
    with make_client() as client:
        response = client.get("/api/dispatch/recommendations/191")

    assert response.status_code == 200
    payload = response.json()
    assert payload["recommended_technician_id"] is None
    assert payload["eligible_candidates"] == []
    assert all(
        "missing_required_certification" in candidate["exclusion_reasons"]
        for candidate in payload["excluded_candidates"]
    )


def test_remote_ticket_enforces_service_radius() -> None:
    with make_client() as client:
        response = client.get("/api/dispatch/recommendations/190")

    assert response.status_code == 200
    payload = response.json()
    assert payload["recommended_technician_id"] is None
    assert any(
        "outside_service_radius" in candidate["exclusion_reasons"]
        and candidate["matched_certification_ids"] == ["CERT-GEN-2"]
        for candidate in payload["excluded_candidates"]
    )


def test_invalid_site_location_blocks_every_candidate() -> None:
    with make_client() as client:
        response = client.get("/api/dispatch/recommendations/196")

    assert response.status_code == 200
    payload = response.json()
    assert payload["eligible_candidates"] == []
    assert all(
        "site_location_unavailable" in candidate["exclusion_reasons"]
        for candidate in payload["excluded_candidates"]
    )


def test_schedule_conflict_is_reported_as_a_hard_gate() -> None:
    with make_client() as client:
        response = client.get("/api/dispatch/recommendations/186")

    assert response.status_code == 200
    candidate = next(
        item for item in response.json()["excluded_candidates"] if item["technician_id"] == "T-003"
    )
    assert "schedule_conflict" in candidate["exclusion_reasons"]


def test_route_provider_failure_excludes_prequalified_candidates() -> None:
    with make_client() as client:
        response = client.get("/api/dispatch/recommendations/220")

    assert response.status_code == 200
    payload = response.json()
    assert payload["recommended_technician_id"] is None
    assert payload["eligible_candidates"] == []
    assert any(
        candidate["exclusion_reasons"] == ["route_unavailable"]
        and candidate["route_provider"] == "mock"
        for candidate in payload["excluded_candidates"]
    )


def test_closed_and_unknown_tickets_return_explicit_errors() -> None:
    with make_client() as client:
        closed = client.get("/api/dispatch/recommendations/188")
        missing = client.get("/api/dispatch/recommendations/not-real")

    assert closed.status_code == 409
    assert closed.json()["detail"] == "Ticket 188 is completed and cannot be dispatched"
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Ticket not-real was not found"
