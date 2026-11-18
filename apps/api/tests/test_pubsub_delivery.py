"""Push transport consumes validated events and remains safe on replay."""

import asyncio
import base64

from fastapi.testclient import TestClient

from geoops_api import worker_app
from geoops_api.config import Settings
from geoops_api.container import build_container
from geoops_api.domain.models import ApprovalStatus


def test_pubsub_envelope_replay_and_invalid_data(monkeypatch) -> None:
    container = build_container(Settings(_env_file=None))
    monkeypatch.setattr(worker_app, "container", container)

    async def prepare():
        proposal = await container.approval_service.request_assignment(
            ticket_id="184",
            technician_id="T-001",
            reason="Reviewed coverage",
            requested_by="operator",
        )
        await container.approval_service.decide(
            proposal.approval_id,
            decision=ApprovalStatus.APPROVED,
            decided_by="supervisor",
            comment=None,
        )
        return (await container.approval_repository.events())[0]

    event = asyncio.run(prepare())
    payload = {"message": {"data": base64.b64encode(event.model_dump_json().encode()).decode()}}
    with TestClient(worker_app.app) as client:
        assert client.post("/events", json={"message": {"data": "!bad!"}}).status_code == 400
        assert client.post("/events", json=payload).status_code == 204
        assert client.post("/events", json=payload).status_code == 204
    assert len(asyncio.run(container.approval_repository.assignments())) == 1
    asyncio.run(container.approval_repository.store.close())
