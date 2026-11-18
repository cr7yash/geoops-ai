"""Contract and state-machine tests for human approval."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from geoops_api.approvals.interfaces import ApprovalConflictError
from geoops_api.approvals.repository import InMemoryApprovalRepository
from geoops_api.approvals.service import ApprovalService
from geoops_api.config import Settings
from geoops_api.container import build_container
from geoops_api.domain.models import ApprovalStatus
from geoops_api.main import create_app


def make_client() -> TestClient:
    return TestClient(create_app(Settings(_env_file=None)))


def proposal() -> dict[str, str]:
    return {
        "ticket_id": "184",
        "technician_id": "T-001",
        "reason": "Highest ranked eligible technician for the compressor incident.",
        "requested_by": "operator@example.test",
    }


def test_create_list_and_get_pending_approval() -> None:
    with make_client() as client:
        created = client.post("/api/approvals", json=proposal())
        approval_id = created.json()["approval_id"]
        listed = client.get("/api/approvals", params={"status": "pending"})
        fetched = client.get(f"/api/approvals/{approval_id}")

    assert created.status_code == 201
    assert created.json()["status"] == "pending"
    assert created.json()["to_technician_name"] == "James Chen"
    assert created.json()["from_technician_id"] is None
    assert created.json()["evidence"]["policy_version"] == "dispatch-v2-routes"
    assert created.json()["evidence"]["route_is_estimate"] is True
    assert listed.json()["total"] == 1
    assert fetched.json() == created.json()


def test_approve_is_idempotent_and_does_not_execute_assignment() -> None:
    with make_client() as client:
        approval = client.post("/api/approvals", json=proposal()).json()
        decision = {
            "decided_by": "supervisor@example.test",
            "comment": "Coverage and travel time reviewed.",
        }
        first = client.post(f"/api/approvals/{approval['approval_id']}/approve", json=decision)
        repeated = client.post(f"/api/approvals/{approval['approval_id']}/approve", json=decision)
        ticket = client.get("/api/tickets/184")

    assert first.status_code == 200
    assert first.json()["status"] == "approved"
    assert first.json()["version"] == 2
    assert repeated.json() == first.json()
    assert ticket.json()["assignments"] == []


def test_reject_then_approve_is_a_conflict() -> None:
    with make_client() as client:
        approval = client.post("/api/approvals", json=proposal()).json()
        rejected = client.post(
            f"/api/approvals/{approval['approval_id']}/reject",
            json={"decided_by": "supervisor@example.test", "comment": "Hold coverage."},
        )
        approve = client.post(
            f"/api/approvals/{approval['approval_id']}/approve",
            json={"decided_by": "other-supervisor@example.test"},
        )

    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert approve.status_code == 409
    assert "already rejected" in approve.json()["detail"]


def test_duplicate_pending_proposal_is_idempotent() -> None:
    with make_client() as client:
        first = client.post("/api/approvals", json=proposal())
        second = client.post("/api/approvals", json=proposal())

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["approval_id"] == first.json()["approval_id"]


def test_ineligible_and_unknown_targets_are_rejected() -> None:
    with make_client() as client:
        ineligible = client.post(
            "/api/approvals",
            json={**proposal(), "technician_id": "T-015"},
        )
        unknown = client.post(
            "/api/approvals",
            json={**proposal(), "technician_id": "T-999"},
        )

    assert ineligible.status_code == 422
    assert "not eligible" in ineligible.json()["detail"]
    assert unknown.status_code == 404


@pytest.mark.anyio
async def test_expired_approval_cannot_be_decided() -> None:
    now = datetime(2026, 10, 7, 16, 0, tzinfo=UTC)
    current = [now]
    container = build_container(Settings(_env_file=None))
    service = ApprovalService(
        repository=InMemoryApprovalRepository(),
        catalog_service=container.catalog_service,
        dispatch_service=container.dispatch_service,
        ttl=timedelta(minutes=5),
        clock=lambda: current[0],
    )
    approval = await service.request_assignment(
        ticket_id="184",
        technician_id="T-001",
        reason="Validated recommendation",
        requested_by="test-operator",
    )
    current[0] = now + timedelta(minutes=6)

    refreshed = await service.get(approval.approval_id)
    assert refreshed.status == ApprovalStatus.EXPIRED
    with pytest.raises(ApprovalConflictError, match="already expired"):
        await service.decide(
            approval.approval_id,
            decision=ApprovalStatus.APPROVED,
            decided_by="test-supervisor",
            comment=None,
        )


def test_firestore_store_requires_a_project() -> None:
    with pytest.raises(ValidationError, match="GOOGLE_CLOUD_PROJECT"):
        Settings(_env_file=None, approval_store="firestore")
