# Deterministic seed data

`geoops_seed.json` is generated from `geoops_api.seed` using a fixed reference time and stable source records.

Regenerate it from the repository root with:

```bash
make seed
```

The dataset contains 10 customers, 25 sites, 15 technicians, 10 certification types, 55 service tickets, assignments, and SLA events. It includes deliberate edge cases for later dispatch work: an invalid address, simulated route failure, unavailable technician, overlapping assignments, expiring certifications, overdue SLAs, a remote qualified technician scenario, and a ticket with no qualified technician.

