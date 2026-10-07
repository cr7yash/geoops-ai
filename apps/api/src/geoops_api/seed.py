"""Generate the deterministic Phase 2 local dataset."""

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from geoops_api.domain.models import (
    Assignment,
    AssignmentStatus,
    Certification,
    Customer,
    GeoPoint,
    SeedDataset,
    ServiceTicket,
    Site,
    SLAEvent,
    SLAEventType,
    Technician,
    TechnicianCertification,
    TechnicianStatus,
    TicketPriority,
    TicketStatus,
)

REFERENCE_TIME = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
DEFAULT_OUTPUT = Path(__file__).resolve().parents[4] / "data/seed/geoops_seed.json"

CUSTOMER_DATA = (
    ("Northstar Grocers", "Retail", "gold"),
    ("Redwood Health Network", "Healthcare", "platinum"),
    ("Pacific Cold Chain", "Logistics", "platinum"),
    ("Summit Learning Group", "Education", "standard"),
    ("Aperture Manufacturing", "Manufacturing", "gold"),
    ("Harbor Hospitality", "Hospitality", "gold"),
    ("Civic Data Services", "Government", "platinum"),
    ("Evergreen Property Co.", "Property Management", "standard"),
    ("Atlas BioLabs", "Life Sciences", "platinum"),
    ("Mesa Energy Partners", "Energy", "gold"),
)

SITE_DATA = (
    ("San Francisco Market", "100 Market St", "San Francisco", "CA", "94105", 37.7936, -122.3958),
    ("Mission Distribution", "2050 Bryant St", "San Francisco", "CA", "94110", 37.7598, -122.4092),
    ("Oakland Medical Center", "3100 Broadway", "Oakland", "CA", "94611", 37.8202, -122.2678),
    ("Berkeley Clinic", "2120 University Ave", "Berkeley", "CA", "94704", 37.8722, -122.2680),
    ("Richmond Cold Storage", "2700 Regatta Blvd", "Richmond", "CA", "94804", 37.9173, -122.3467),
    ("Hayward Crossdock", "2400 Clawiter Rd", "Hayward", "CA", "94545", 37.6287, -122.1214),
    ("Palo Alto Campus", "50 Embarcadero Rd", "Palo Alto", "CA", "94301", 37.4419, -122.1430),
    ("San Mateo Academy", "400 Mounds Rd", "San Mateo", "CA", "94402", 37.5661, -122.3329),
    ("Fremont Plant", "47500 Kato Rd", "Fremont", "CA", "94538", 37.4818, -121.9368),
    ("San Jose Assembly", "1750 Automation Pkwy", "San Jose", "CA", "95131", 37.3871, -121.9018),
    (
        "Embarcadero Hotel",
        "5 Embarcadero Center",
        "San Francisco",
        "CA",
        "94111",
        37.7955,
        -122.3972,
    ),
    ("Napa Resort", "1600 Atlas Peak Rd", "Napa", "CA", "94558", 38.3446, -122.2628),
    (
        "Civic Operations Center",
        "1 Frank H Ogawa Plaza",
        "Oakland",
        "CA",
        "94612",
        37.8053,
        -122.2725,
    ),
    ("Data Archive", "2001 Broadway", "Oakland", "CA", "94612", 37.8098, -122.2685),
    ("Marina Towers", "1350 Franklin St", "San Francisco", "CA", "94109", 37.7873, -122.4233),
    ("Walnut Creek Offices", "1350 Treat Blvd", "Walnut Creek", "CA", "94597", 37.9259, -122.0575),
    ("South Bay Laboratory", "3333 Scott Blvd", "Santa Clara", "CA", "95054", 37.3797, -121.9829),
    (
        "Genomics Annex",
        "7000 Shoreline Ct",
        "South San Francisco",
        "CA",
        "94080",
        37.6688,
        -122.3877,
    ),
    ("Concord Solar Depot", "2300 Stanwell Dr", "Concord", "CA", "94520", 37.9808, -122.0516),
    ("Antioch Field Office", "300 G St", "Antioch", "CA", "94509", 38.0166, -121.8155),
    (
        "Daly City Market",
        "1901 Junipero Serra Blvd",
        "Daly City",
        "CA",
        "94014",
        37.6787,
        -122.4716,
    ),
    ("San Rafael Clinic", "1000 Northgate Dr", "San Rafael", "CA", "94903", 38.0080, -122.5450),
    ("Route Failure Lab", "42 Signal Way", "Mountain View", "CA", "94043", 37.4140, -122.0780),
    ("Legacy Address Site", "Unknown Service Road", "Brisbane", "CA", "94005", None, None),
    ("Remote Pump Station", "8800 Tesla Rd", "Livermore", "CA", "94550", 37.6250, -121.6500),
)

CERTIFICATION_DATA = (
    ("CERT-HVAC-1", "Commercial HVAC I", "NATE", ["hvac", "compressor"]),
    ("CERT-REFRIG", "EPA Refrigerant 608", "EPA", ["compressor", "refrigeration"]),
    ("CERT-GEN-2", "Generator Systems II", "EGSA", ["generator"]),
    ("CERT-HV", "High Voltage Electrical", "NFPA", ["electrical", "solar_inverter"]),
    ("CERT-FIRE", "Fire Suppression Systems", "NFPA", ["fire_suppression"]),
    ("CERT-NET", "Low Voltage Network", "BICSI", ["network", "controls"]),
    ("CERT-BOILER", "Commercial Boiler", "ASME", ["boiler"]),
    ("CERT-PUMP", "Industrial Pump Service", "HI", ["pump"]),
    ("CERT-ELEVATOR", "Elevator Drive Systems", "NAEC", ["elevator"]),
    ("CERT-OSHA", "OSHA 30", "OSHA", ["safety"]),
)

TECHNICIAN_DATA = (
    ("T-001", "James Chen", "San Francisco", 37.7810, -122.4110, ["hvac", "controls"], 184, 4.8),
    ("T-002", "Maya Patel", "Oakland", 37.8044, -122.2712, ["generator", "electrical"], 156, 4.9),
    ("T-003", "Luis Romero", "San Jose", 37.3382, -121.8863, ["hvac", "refrigeration"], 211, 4.7),
    ("T-004", "Avery Brooks", "Berkeley", 37.8715, -122.2730, ["network", "controls"], 98, 4.6),
    ("T-005", "Priya Nair", "Fremont", 37.5485, -121.9886, ["boiler", "pump"], 143, 4.8),
    (
        "T-006",
        "Noah Williams",
        "Napa",
        38.2975,
        -122.2869,
        ["fire_suppression", "safety"],
        121,
        4.5,
    ),
    (
        "T-007",
        "Sofia Martinez",
        "San Mateo",
        37.5630,
        -122.3255,
        ["hvac", "refrigeration"],
        177,
        4.9,
    ),
    (
        "T-008",
        "Ethan Kim",
        "Santa Clara",
        37.3541,
        -121.9552,
        ["electrical", "solar_inverter"],
        165,
        4.7,
    ),
    ("T-009", "Zoe Thompson", "Richmond", 37.9358, -122.3477, ["generator", "pump"], 132, 4.6),
    ("T-010", "Marcus Reed", "Walnut Creek", 37.9101, -122.0652, ["boiler", "hvac"], 201, 4.8),
    ("T-011", "Hannah Lee", "Daly City", 37.6879, -122.4702, ["network", "controls"], 89, 4.7),
    ("T-012", "Owen Garcia", "Concord", 37.9780, -122.0311, ["generator", "electrical"], 148, 4.6),
    (
        "T-013",
        "Nina Shah",
        "Palo Alto",
        37.4419,
        -122.1430,
        ["fire_suppression", "safety"],
        102,
        4.8,
    ),
    ("T-014", "Caleb Foster", "Hayward", 37.6688, -122.0808, ["pump", "boiler"], 119, 4.5),
    ("T-015", "Riley Morgan", "San Rafael", 37.9735, -122.5311, ["hvac", "generator"], 172, 4.7),
)

CERTIFICATE_MAP = {
    "T-001": ["CERT-HVAC-1", "CERT-REFRIG", "CERT-NET", "CERT-OSHA"],
    "T-002": ["CERT-GEN-2", "CERT-HV", "CERT-OSHA"],
    "T-003": ["CERT-HVAC-1", "CERT-REFRIG", "CERT-OSHA"],
    "T-004": ["CERT-NET", "CERT-OSHA"],
    "T-005": ["CERT-BOILER", "CERT-PUMP", "CERT-OSHA"],
    "T-006": ["CERT-FIRE", "CERT-OSHA"],
    "T-007": ["CERT-HVAC-1", "CERT-REFRIG"],
    "T-008": ["CERT-HV", "CERT-OSHA"],
    "T-009": ["CERT-GEN-2", "CERT-PUMP", "CERT-OSHA"],
    "T-010": ["CERT-BOILER", "CERT-HVAC-1", "CERT-OSHA"],
    "T-011": ["CERT-NET", "CERT-OSHA"],
    "T-012": ["CERT-GEN-2", "CERT-HV", "CERT-OSHA"],
    "T-013": ["CERT-FIRE", "CERT-OSHA"],
    "T-014": ["CERT-PUMP", "CERT-BOILER", "CERT-OSHA"],
    "T-015": ["CERT-HVAC-1", "CERT-GEN-2", "CERT-OSHA"],
}

EQUIPMENT = (
    ("compressor", "CERT-REFRIG", "Compressor pressure loss"),
    ("hvac", "CERT-HVAC-1", "Rooftop unit airflow fault"),
    ("generator", "CERT-GEN-2", "Backup generator start failure"),
    ("electrical", "CERT-HV", "Main switchgear alarm"),
    ("fire_suppression", "CERT-FIRE", "Suppression panel trouble signal"),
    ("network", "CERT-NET", "Building controller offline"),
    ("boiler", "CERT-BOILER", "Boiler ignition lockout"),
    ("pump", "CERT-PUMP", "Circulation pump vibration"),
)


def build_seed_dataset() -> SeedDataset:
    customers = [
        Customer(
            customer_id=f"C-{index:03d}",
            name=name,
            industry=industry,
            service_tier=tier,
        )
        for index, (name, industry, tier) in enumerate(CUSTOMER_DATA, start=1)
    ]

    sites: list[Site] = []
    for index, (name, address, city, state, postal_code, latitude, longitude) in enumerate(
        SITE_DATA, start=1
    ):
        location = (
            GeoPoint(latitude=latitude, longitude=longitude)
            if latitude is not None and longitude is not None
            else None
        )
        sites.append(
            Site(
                site_id=f"S-{index:03d}",
                customer_id=f"C-{((index - 1) % len(customers)) + 1:03d}",
                name=name,
                address=address,
                city=city,
                state=state,
                postal_code=postal_code,
                location=location,
                geocode_status="invalid" if index == 24 else "valid",
                routing_mode="simulate_failure" if index == 23 else "normal",
            )
        )

    certifications = [
        Certification(
            certification_id=certification_id,
            name=name,
            issuing_body=issuer,
            equipment_types=equipment_types,
        )
        for certification_id, name, issuer, equipment_types in CERTIFICATION_DATA
    ]

    technician_statuses = (
        TechnicianStatus.AVAILABLE,
        TechnicianStatus.DISPATCHED,
        TechnicianStatus.DISPATCHED,
        TechnicianStatus.AVAILABLE,
        TechnicianStatus.AVAILABLE,
        TechnicianStatus.OFF_DUTY,
        TechnicianStatus.AVAILABLE,
        TechnicianStatus.DISPATCHED,
        TechnicianStatus.AVAILABLE,
        TechnicianStatus.AVAILABLE,
        TechnicianStatus.AVAILABLE,
        TechnicianStatus.DISPATCHED,
        TechnicianStatus.AVAILABLE,
        TechnicianStatus.AVAILABLE,
        TechnicianStatus.UNAVAILABLE,
    )
    technicians = [
        Technician(
            technician_id=technician_id,
            name=name,
            email=f"{name.lower().replace(' ', '.')}@geoops.example",
            phone=f"+1-415-555-{1000 + index:04d}",
            status=technician_statuses[index - 1],
            home_city=city,
            current_location=GeoPoint(latitude=latitude, longitude=longitude),
            skill_tags=skills,
            completed_jobs=jobs,
            average_rating=rating,
        )
        for index, (
            technician_id,
            name,
            city,
            latitude,
            longitude,
            skills,
            jobs,
            rating,
        ) in enumerate(TECHNICIAN_DATA, start=1)
    ]

    technician_certifications: list[TechnicianCertification] = []
    for technician_id, certification_ids in CERTIFICATE_MAP.items():
        for certification_id in certification_ids:
            expires_on = date(2026, 10, 15) if technician_id == "T-007" else date(2028, 6, 30)
            technician_certifications.append(
                TechnicianCertification(
                    technician_id=technician_id,
                    certification_id=certification_id,
                    issued_on=date(2024, 7, 1),
                    expires_on=expires_on,
                )
            )

    priorities = (
        TicketPriority.CRITICAL,
        TicketPriority.HIGH,
        TicketPriority.MEDIUM,
        TicketPriority.LOW,
    )
    statuses = (
        TicketStatus.OPEN,
        TicketStatus.ASSIGNED,
        TicketStatus.IN_PROGRESS,
        TicketStatus.ON_HOLD,
        TicketStatus.COMPLETED,
    )
    tickets: list[ServiceTicket] = []
    for offset in range(55):
        ticket_id = str(184 + offset)
        site = sites[(offset + 11) % len(sites)]
        equipment_type, certification_id, title = EQUIPMENT[offset % len(EQUIPMENT)]
        status = statuses[offset % len(statuses)]
        created_at = REFERENCE_TIME - timedelta(hours=offset * 3 + 2)
        response_due_at = created_at + timedelta(hours=2 + (offset % 3) * 2)
        resolution_due_at = created_at + timedelta(hours=8 + (offset % 4) * 8)
        if offset == 0:
            site = sites[11]
            equipment_type, certification_id, title = EQUIPMENT[0]
            status = TicketStatus.OPEN
        if offset == 6:
            site = sites[24]
            equipment_type, certification_id, title = (
                "generator",
                "CERT-GEN-2",
                "Remote generator fuel-control fault",
            )
        if offset == 7:
            equipment_type, certification_id, title = (
                "elevator",
                "CERT-ELEVATOR",
                "Elevator drive fault",
            )
            status = TicketStatus.OPEN
        tickets.append(
            ServiceTicket(
                ticket_id=ticket_id,
                customer_id=site.customer_id,
                site_id=site.site_id,
                title=title,
                description=f"Automated monitoring and site staff reported {title.lower()}.",
                equipment_type=equipment_type,
                equipment_id=f"EQ-{site.site_id[2:]}-{(offset % 4) + 1:02d}",
                required_certification_ids=[certification_id],
                priority=priorities[offset % len(priorities)],
                status=status,
                created_at=created_at,
                response_due_at=response_due_at,
                resolution_due_at=resolution_due_at,
            )
        )

    assignments: list[Assignment] = []
    assignment_index = 1
    for offset, ticket in enumerate(tickets):
        if ticket.status not in {
            TicketStatus.ASSIGNED,
            TicketStatus.IN_PROGRESS,
            TicketStatus.COMPLETED,
        }:
            continue
        assignment_status = (
            AssignmentStatus.COMPLETED
            if ticket.status == TicketStatus.COMPLETED
            else AssignmentStatus.ACTIVE
        )
        technician_id = f"T-{(offset % 14) + 1:03d}"
        assignments.append(
            Assignment(
                assignment_id=f"A-{assignment_index:04d}",
                ticket_id=ticket.ticket_id,
                technician_id=technician_id,
                scheduled_start=ticket.created_at + timedelta(hours=2),
                scheduled_end=ticket.created_at + timedelta(hours=6),
                status=assignment_status,
                created_at=ticket.created_at + timedelta(minutes=20),
            )
        )
        assignment_index += 1

    # Explicit overlapping active work demonstrates conflict detection in Phase 3.
    conflict_start = REFERENCE_TIME + timedelta(hours=1)
    for ticket_id in ("186", "187"):
        assignments.append(
            Assignment(
                assignment_id=f"A-{assignment_index:04d}",
                ticket_id=ticket_id,
                technician_id="T-003",
                scheduled_start=conflict_start,
                scheduled_end=conflict_start + timedelta(hours=3),
                status=AssignmentStatus.ACTIVE,
                created_at=REFERENCE_TIME - timedelta(hours=1),
            )
        )
        assignment_index += 1

    sla_events: list[SLAEvent] = []
    for index, ticket in enumerate(tickets, start=1):
        sla_events.extend(
            (
                SLAEvent(
                    event_id=f"SLA-{index:03d}-01",
                    ticket_id=ticket.ticket_id,
                    event_type=SLAEventType.CREATED,
                    occurred_at=ticket.created_at,
                ),
                SLAEvent(
                    event_id=f"SLA-{index:03d}-02",
                    ticket_id=ticket.ticket_id,
                    event_type=SLAEventType.RESOLUTION_DUE,
                    occurred_at=ticket.created_at,
                    deadline_at=ticket.resolution_due_at,
                ),
            )
        )
        if ticket.status != TicketStatus.COMPLETED and ticket.resolution_due_at < REFERENCE_TIME:
            sla_events.append(
                SLAEvent(
                    event_id=f"SLA-{index:03d}-03",
                    ticket_id=ticket.ticket_id,
                    event_type=SLAEventType.BREACHED,
                    occurred_at=ticket.resolution_due_at,
                    deadline_at=ticket.resolution_due_at,
                    metadata={"reason": "resolution_deadline_exceeded"},
                )
            )

    return SeedDataset(
        seed_version="2026.10.phase2",
        reference_time=REFERENCE_TIME,
        customers=customers,
        sites=sites,
        certifications=certifications,
        technician_certifications=technician_certifications,
        technicians=technicians,
        service_tickets=tickets,
        assignments=assignments,
        sla_events=sla_events,
    )


def write_seed_dataset(output_path: Path = DEFAULT_OUTPUT) -> SeedDataset:
    dataset = build_seed_dataset()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(dataset.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return dataset


def main() -> None:
    dataset = write_seed_dataset()
    print(
        "Generated deterministic seed data: "
        f"{len(dataset.customers)} customers, {len(dataset.sites)} sites, "
        f"{len(dataset.technicians)} technicians, "
        f"{len(dataset.service_tickets)} tickets."
    )


if __name__ == "__main__":
    main()
