# Async dispatch

Approval commits a `dispatch.approved` event in the same transaction as the approval decision. The relay publishes unpublished events and marks them delivered only after the transport accepts them. A process crash between those steps causes a duplicate delivery, which the consumer handles safely.

The worker loads the authoritative approval, rechecks eligibility and the current assignee, then atomically writes the assignment, terminal approval status, and historical event. A shared revision prevents two workers from booking a technician from stale schedule snapshots. A revision conflict retries through the transport. A business-rule failure records `failed` and never writes an assignment.

Local mode uses SQLite with WAL and an in-memory transport. `WORKER_ENABLED=true` runs the relay in the API lifespan. `STATE_DATABASE_PATH` preserves state across restarts. Tests use isolated in-memory SQLite databases.

Cloud mode uses Firestore transactions and Pub/Sub. The private worker service exposes `/events` for authenticated push and `/relay` for Cloud Scheduler. Cloud Run IAM validates the caller's identity. Pub/Sub retries non-success responses; the subscription's dead-letter policy bounds delivery attempts.

The JSON seed remains immutable. Catalog reads combine the seed snapshot with operational assignment overrides. Historical records are retained separately from the mutable assignment document.
