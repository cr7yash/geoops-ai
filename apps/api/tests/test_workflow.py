"""Run the real approval → outbox → worker path, including replay and recovery."""

import asyncio
from pathlib import Path

import pytest

from geoops_api.approvals.interfaces import ApprovalConflictError
from geoops_api.config import Settings
from geoops_api.container import build_container
from geoops_api.domain.models import ApprovalStatus


@pytest.mark.anyio
async def test_approved_outbox_executes_once_and_survives_restart(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None, approval_store="sqlite", state_database_path=tmp_path / "state.db"
    )
    first = build_container(settings)
    proposal = await first.approval_service.request_assignment(
        ticket_id="184", technician_id="T-001", reason="Coverage reviewed", requested_by="operator"
    )
    assert await first.approval_repository.events() == []
    await first.approval_service.decide(
        proposal.approval_id,
        decision=ApprovalStatus.APPROVED,
        decided_by="supervisor",
        comment=None,
    )
    assert len(await first.approval_repository.events()) == 1
    await first.approval_repository.store.close()
    recovered = build_container(settings)
    assert await recovered.outbox_relay.run_once() == 1
    event = (await recovered.approval_repository.events())[0]
    await recovered.dispatch_worker.consume(event)
    await recovered.dispatch_worker.consume(event)
    assert await recovered.outbox_relay.run_once() == 0
    result = await recovered.approval_service.get(proposal.approval_id)
    assert result.status == ApprovalStatus.EXECUTED
    ticket = await recovered.catalog_service.get_ticket("184")
    assert ticket and len(ticket.assignments) == 1
    assert ticket.assignments[0].technician_id == "T-001"
    assert len(await recovered.approval_repository.store.scan("history")) == 1
    await recovered.approval_repository.store.close()


@pytest.mark.anyio
async def test_pending_or_rejected_proposals_never_publish() -> None:
    container = build_container(Settings(_env_file=None))
    approval = await container.approval_service.request_assignment(
        ticket_id="184", technician_id="T-001", reason="Review needed", requested_by="operator"
    )
    await container.approval_service.decide(
        approval.approval_id,
        decision=ApprovalStatus.REJECTED,
        decided_by="supervisor",
        comment="Hold",
    )
    assert await container.outbox_relay.run_once() == 0
    assert await container.approval_repository.assignments() == []
    await container.approval_repository.store.close()


@pytest.mark.anyio
async def test_concurrent_opposite_decisions_have_one_winner() -> None:
    container = build_container(Settings(_env_file=None))
    approval = await container.approval_service.request_assignment(
        ticket_id="184", technician_id="T-001", reason="Review needed", requested_by="operator"
    )
    results = await asyncio.gather(
        *[
            container.approval_service.decide(
                approval.approval_id, decision=decision, decided_by="supervisor", comment=None
            )
            for decision in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED)
        ],
        return_exceptions=True,
    )
    assert sum(isinstance(item, ApprovalConflictError) for item in results) == 1
    final = await container.approval_service.get(approval.approval_id)
    assert len(await container.approval_repository.events()) == (
        final.status == ApprovalStatus.APPROVED
    )
    await container.approval_repository.store.close()
