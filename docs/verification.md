# Verification record

The implementation was verified locally on November 17, 2026. This record distinguishes executed checks from cloud and container checks that require another environment.

## Executed checks

- Python lint and formatting passed, including the reusable acceptance scripts.
- Strict mypy checks passed across the API package.
- API tests passed for health, catalogs, maps, knowledge, agent tools, human decisions, outbox recovery, replay, transport retries, authentication, and evaluation.
- Web ESLint and TypeScript checks passed.
- All 18 web tests passed, including approval decisions and measured evaluation output.
- The optimized Next.js build and Python source distribution and wheel build passed.
- All 12 labeled evaluation scenarios passed the configured regression thresholds.
- The live acceptance script passed through the real web proxy, created and approved a proposal, observed worker execution, confirmed the assignment, ran evaluation, and loaded the agent, approval, and evaluation pages.
- Terraform formatting and schema validation passed with the locked Google provider. The mocked plan test passed for private operator access, bounded retries, protected source documents, and scale to zero.
- The generated BigQuery table schemas match the canonical SQL DDL.
- The production JavaScript dependency audit reported no known vulnerabilities after updating Next.js to 16.4.6 and React to 19.3.1.

## Reproduce

Run `make lint`, `make typecheck`, `make test`, `make eval`, `make build`, and `make verify`. The underlying package scripts work without Make. Run Terraform checks as listed in the root README. The acceptance script owns temporary state and stops its web and API processes.

## Checks awaiting an equipped environment

Docker and the Google Cloud CLI were not installed on the implementation machine. Compose execution and all four image builds are configured in repository CI but were not marked as passing locally. Terraform ran with a mocked provider; no infrastructure was applied.

No GCP project or provider credentials were supplied. Firestore transactions, Pub/Sub delivery, BigQuery SQL, GCS ingestion, Google embeddings, Google Maps, Vertex AI, and Gemini Developer API calls need managed-provider integration checks in the deployment project. API integration tests and the live acceptance flow use local adapters.

Browser automation was unavailable. Component tests, framework builds, rendered HTTP responses, and the live server proxy were checked; screenshot and interactive-browser review remain separate checks.

## Scope limits

The catalog adapter reads a bounded synthetic snapshot. SLA decisions use its reference clock. Evaluation labels cover the committed scenarios and citation metadata, not an independent semantic assessment of arbitrary model answers. Reviewer labels are explicit request data behind service authentication. The cloud web service is private by default.
