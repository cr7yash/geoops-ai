# Deploy GeoOps on Google Cloud

The Terraform configuration creates private Cloud Run API, web, and dispatch services, an ingestion job, Firestore, BigQuery tables, a versioned document bucket, Pub/Sub delivery with a dead-letter subscription, Artifact Registry, Secret Manager entries, service identities, and a dispatch-failure alert. Cloud Scheduler invokes the outbox relay once per minute.

## Prepare the project

Use a billing-enabled Google Cloud project and credentials that can enable services and create the declared resources. Install Terraform 1.9 or newer, Google Cloud CLI, Docker, pnpm, uv, Node 24, and Python 3.13.

1. Run `gcloud auth login` and `gcloud auth application-default login`.
2. Set the project with `gcloud config set project YOUR_PROJECT_ID`.
3. Copy `infrastructure/terraform/terraform.tfvars.example` to `infrastructure/terraform/terraform.tfvars` and replace the project, image references, and allowed operator identities.
4. Run `terraform -chdir=infrastructure/terraform init`.

Terraform state can contain resource configuration. Configure a private remote backend before team use. Never commit state, plans, credentials, or the populated variable file.

## Bootstrap the registry and secrets

Cloud Run needs existing images and secret versions. The initial resource bootstrap therefore precedes the complete apply.

```bash
terraform -chdir=infrastructure/terraform apply \
  -target=google_project_service.api \
  -target=google_service_account.service \
  -target=google_artifact_registry_repository.images \
  -target=google_secret_manager_secret.secret
openssl rand -hex 32 | gcloud secrets versions add geoops-api-token --data-file=-
gcloud builds submit --config=cloudbuild.yaml --substitutions=_DEPLOY=false
```

Use a pinned image tag returned by the build in the Terraform variable file. Cloud Build defaults to its configured build identity; select the `geoops-build` identity after its IAM bindings exist. The build identity needs Artifact Registry write access, Cloud Logging write access, Cloud Run developer access, and permission to act as the runtime identities. Bootstrap commands require operator credentials until those bindings exist.

For `model_provider=gemini_api`, add a `gemini-api-key` secret version before creating services. For `maps_provider=google`, add a `google-maps-api-key` secret version. Read keys from stdin with `gcloud secrets versions add NAME --data-file=-` rather than placing key values in command arguments or Terraform.

## Apply and load the simulation

```bash
terraform -chdir=infrastructure/terraform plan -out=reviewed.tfplan
terraform -chdir=infrastructure/terraform apply reviewed.tfplan
```

The configuration enables deletion protection on stateful resources and Cloud Run services. Import an existing default Firestore database rather than trying to recreate it.

Populate the synthetic catalog and source documents after the tables and bucket exist:

```bash
uv run --package geoops-api python -m geoops_api.bootstrap --replace
gcloud storage rsync --recursive data/documents gs://YOUR_DOCUMENT_BUCKET
gcloud run jobs execute geoops-ingestion --region=us-central1 --wait
gcloud run services proxy geoops-web --region=us-central1 --port=3000
```

Set `GOOGLE_CLOUD_PROJECT` and `BIGQUERY_DATASET` before the bootstrap command. `--replace` overwrites the synthetic catalog rows using the table definitions in `infrastructure/terraform/tables.json`. If an earlier bootstrap inferred the geography columns as strings, rerun the corrected command against the synthetic catalog to restore the declared types. The ingestion job replaces the knowledge index rows atomically and preserves the table schema and partitioning. Use matching embedding provider, model, and dimensions for ingestion and search.

Open `http://localhost:3000` through the authenticated proxy. The server uses a Cloud Run identity token to invoke the private API. The API also verifies `X-Geoops-Token`, supplied from Secret Manager by the web server. The service token never enters browser assets.

## Release subsequent changes

`cloudbuild.yaml` runs web lint, type checks, tests, Python checks, and the deterministic evaluation gate before building images. Set `_DEPLOY=true` to update the existing Cloud Run services and ingestion job. A failed evaluation stops the release before image deployment.

Use Terraform to change service configuration and IAM. Use Cloud Build to update verified image revisions. Reapply with the current image variables after a release to keep Terraform's state consistent with the deployed revisions.

## IAM and operational limits

Each runtime has its own service account. API, worker, and ingestion identities access only the GeoOps BigQuery dataset. The API and ingestion identities can read the source bucket. Pub/Sub can invoke the private worker, and the worker can publish the approved-dispatch topic. Secret access is granted per secret and identity. The web identity can invoke the API.

Operator identities are IAM principals at the web-service boundary. Reviewer names stored with decisions are audit labels supplied by an authenticated operator; they are not independently verified application accounts.

The SQL catalog is a bounded simulation snapshot with a 30-second refresh interval and a 10,000-row limit per table. Firestore stores operational overlays and workflow state. This implementation is intended for the supplied synthetic dataset. Benchmark and redesign the snapshot reader before loading a large live catalog.

## Recover failed delivery

Inspect the `dispatch-dead-letter-inspect` subscription for Pub/Sub messages that exhaust retries. Check the approval's `execution_error` before redelivery. A terminal business-rule failure needs a new reviewed proposal. Redelivering an already executed event is safe.

The local outbox uses exponential backoff up to ten attempts and keeps exhausted events in state. Back up the SQLite file before manual recovery. Cloud Run uses Pub/Sub retry and dead-letter settings in addition to outbox publication retries.

Structured stdout logs appear in Cloud Logging. Search by `trace_id`, `agent_run_id`, `approval_id`, or `event_id`. The Terraform alert detects dispatch failures; attach a notification channel appropriate to your environment.

The source configuration can be validated without creating resources. Actual credentials, image builds, resource provisioning, managed model calls, and deployed connectivity need separate verification in your project.
