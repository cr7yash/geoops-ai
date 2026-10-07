"""Determinism and referential-integrity tests for synthetic operations data."""

from geoops_api.domain.models import AssignmentStatus, TechnicianStatus
from geoops_api.seed import REFERENCE_TIME, build_seed_dataset


def test_seed_dataset_is_deterministic_and_has_expected_scale() -> None:
    first = build_seed_dataset()
    second = build_seed_dataset()

    assert first == second
    assert len(first.customers) == 10
    assert len(first.sites) == 25
    assert len(first.technicians) == 15
    assert len(first.certifications) == 10
    assert len(first.service_tickets) == 55
    assert len(first.assignments) >= 30
    assert len(first.sla_events) >= 110


def test_seed_relationships_are_referentially_valid() -> None:
    dataset = build_seed_dataset()
    customer_ids = {item.customer_id for item in dataset.customers}
    site_ids = {item.site_id for item in dataset.sites}
    technician_ids = {item.technician_id for item in dataset.technicians}
    ticket_ids = {item.ticket_id for item in dataset.service_tickets}
    certification_ids = {item.certification_id for item in dataset.certifications}

    assert all(site.customer_id in customer_ids for site in dataset.sites)
    assert all(ticket.customer_id in customer_ids for ticket in dataset.service_tickets)
    assert all(ticket.site_id in site_ids for ticket in dataset.service_tickets)
    assert all(
        set(ticket.required_certification_ids) <= certification_ids
        for ticket in dataset.service_tickets
    )
    assert all(item.ticket_id in ticket_ids for item in dataset.assignments)
    assert all(item.technician_id in technician_ids for item in dataset.assignments)


def test_seed_contains_required_edge_cases() -> None:
    dataset = build_seed_dataset()

    assert any(site.geocode_status == "invalid" for site in dataset.sites)
    assert any(site.routing_mode == "simulate_failure" for site in dataset.sites)
    assert any(
        technician.status == TechnicianStatus.UNAVAILABLE for technician in dataset.technicians
    )
    assert any(event.event_type == "breached" for event in dataset.sla_events)
    assert not any(
        certification.certification_id == "CERT-ELEVATOR"
        for certification in dataset.technician_certifications
    )

    conflicts = [
        assignment
        for assignment in dataset.assignments
        if assignment.technician_id == "T-003"
        and assignment.status == AssignmentStatus.ACTIVE
        and assignment.ticket_id in {"186", "187"}
        and assignment.scheduled_start == REFERENCE_TIME.replace(hour=13)
    ]
    assert len(conflicts) == 2
    assert conflicts[0].scheduled_start == conflicts[1].scheduled_start
