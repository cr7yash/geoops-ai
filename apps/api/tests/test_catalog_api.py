"""Integration tests for the Phase 2 catalog APIs."""

from fastapi.testclient import TestClient

from geoops_api.config import Settings
from geoops_api.main import create_app


def make_client() -> TestClient:
    return TestClient(create_app(Settings(_env_file=None)))


def test_ticket_list_supports_pagination_and_filters() -> None:
    with make_client() as client:
        response = client.get("/api/tickets", params={"limit": 5, "priority": "critical"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 5
    assert payload["offset"] == 0
    assert payload["total"] > 5
    assert len(payload["items"]) == 5
    assert {item["priority"] for item in payload["items"]} == {"critical"}


def test_ticket_detail_includes_related_operational_context() -> None:
    with make_client() as client:
        response = client.get("/api/tickets/184")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticket_id"] == "184"
    assert payload["equipment_type"] == "compressor"
    assert payload["site"]["site_id"] == "S-012"
    assert payload["customer_name"]
    assert payload["sla_state"] in {"overdue", "at_risk", "on_track", "met"}


def test_ticket_search_and_not_found_contract() -> None:
    with make_client() as client:
        search_response = client.get("/api/tickets", params={"query": "elevator"})
        missing_response = client.get("/api/tickets/does-not-exist")

    assert search_response.status_code == 200
    assert search_response.json()["items"][0]["ticket_id"] == "191"
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "Ticket does-not-exist was not found"


def test_technician_list_exposes_certifications_and_workload() -> None:
    with make_client() as client:
        response = client.get("/api/technicians", params={"status": "available"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] > 0
    assert {item["status"] for item in payload["items"]} == {"available"}
    assert all("certifications" in item for item in payload["items"])
    assert all("active_assignment_count" in item for item in payload["items"])


def test_technician_detail_marks_soon_to_expire_certifications() -> None:
    with make_client() as client:
        response = client.get("/api/technicians/T-007")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Sofia Martinez"
    assert {item["validity"] for item in payload["certifications"]} == {"expiring_soon"}


def test_no_technician_holds_elevator_certification() -> None:
    with make_client() as client:
        response = client.get("/api/technicians", params={"certification_id": "CERT-ELEVATOR"})

    assert response.status_code == 200
    assert response.json()["total"] == 0
