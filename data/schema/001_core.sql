-- GeoOps AI BigQuery analytical schema
-- Replace `${PROJECT_ID}` and `${DATASET_ID}` before execution.

CREATE SCHEMA IF NOT EXISTS `${PROJECT_ID}.${DATASET_ID}`
OPTIONS (
  location = "US",
  description = "GeoOps analytical, historical, and retrieval data"
);

CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${DATASET_ID}.customers` (
  customer_id STRING NOT NULL,
  name STRING NOT NULL,
  industry STRING NOT NULL,
  service_tier STRING NOT NULL,
  active BOOL NOT NULL,
  updated_at TIMESTAMP NOT NULL
)
CLUSTER BY customer_id, service_tier;

CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${DATASET_ID}.sites` (
  site_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  name STRING NOT NULL,
  address STRING NOT NULL,
  city STRING NOT NULL,
  state STRING NOT NULL,
  postal_code STRING NOT NULL,
  timezone STRING NOT NULL,
  location GEOGRAPHY,
  geocode_status STRING NOT NULL,
  routing_mode STRING NOT NULL,
  updated_at TIMESTAMP NOT NULL
)
CLUSTER BY customer_id, state, city;

CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${DATASET_ID}.certifications` (
  certification_id STRING NOT NULL,
  name STRING NOT NULL,
  issuing_body STRING NOT NULL,
  equipment_types ARRAY<STRING> NOT NULL,
  updated_at TIMESTAMP NOT NULL
)
CLUSTER BY certification_id;

CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${DATASET_ID}.technicians` (
  technician_id STRING NOT NULL,
  name STRING NOT NULL,
  email STRING NOT NULL,
  phone STRING NOT NULL,
  status STRING NOT NULL,
  home_city STRING NOT NULL,
  current_location GEOGRAPHY NOT NULL,
  skill_tags ARRAY<STRING> NOT NULL,
  completed_jobs INT64 NOT NULL,
  average_rating FLOAT64 NOT NULL,
  updated_at TIMESTAMP NOT NULL
)
CLUSTER BY status, home_city;

CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${DATASET_ID}.technician_certifications` (
  technician_id STRING NOT NULL,
  certification_id STRING NOT NULL,
  issued_on DATE NOT NULL,
  expires_on DATE NOT NULL,
  updated_at TIMESTAMP NOT NULL
)
CLUSTER BY technician_id, certification_id;

CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${DATASET_ID}.service_tickets` (
  ticket_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  site_id STRING NOT NULL,
  title STRING NOT NULL,
  description STRING NOT NULL,
  equipment_type STRING NOT NULL,
  equipment_id STRING NOT NULL,
  required_certification_ids ARRAY<STRING> NOT NULL,
  priority STRING NOT NULL,
  status STRING NOT NULL,
  created_at TIMESTAMP NOT NULL,
  response_due_at TIMESTAMP NOT NULL,
  resolution_due_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(created_at)
CLUSTER BY status, priority, customer_id, site_id;

CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${DATASET_ID}.assignments` (
  assignment_id STRING NOT NULL,
  ticket_id STRING NOT NULL,
  technician_id STRING NOT NULL,
  scheduled_start TIMESTAMP NOT NULL,
  scheduled_end TIMESTAMP NOT NULL,
  status STRING NOT NULL,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(scheduled_start)
CLUSTER BY technician_id, ticket_id, status;

CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${DATASET_ID}.sla_events` (
  event_id STRING NOT NULL,
  ticket_id STRING NOT NULL,
  event_type STRING NOT NULL,
  occurred_at TIMESTAMP NOT NULL,
  deadline_at TIMESTAMP,
  metadata JSON
)
PARTITION BY DATE(occurred_at)
CLUSTER BY ticket_id, event_type;

CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${DATASET_ID}.agent_runs` (
  agent_run_id STRING NOT NULL,
  session_id STRING NOT NULL,
  started_at TIMESTAMP NOT NULL,
  completed_at TIMESTAMP,
  status STRING NOT NULL,
  model STRING,
  tool_names ARRAY<STRING>,
  tokens_in INT64,
  tokens_out INT64,
  latency_ms FLOAT64,
  success BOOL,
  error_type STRING
)
PARTITION BY DATE(started_at)
CLUSTER BY status, model;

CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${DATASET_ID}.eval_results` (
  evaluation_result_id STRING NOT NULL,
  evaluation_run_id STRING NOT NULL,
  case_id STRING NOT NULL,
  created_at TIMESTAMP NOT NULL,
  task_success BOOL NOT NULL,
  tool_selection_accuracy FLOAT64,
  tool_argument_accuracy FLOAT64,
  retrieval_recall FLOAT64,
  citation_correctness FLOAT64,
  policy_compliance FLOAT64,
  latency_ms FLOAT64,
  token_usage INT64,
  estimated_cost_usd NUMERIC,
  metrics JSON
)
PARTITION BY DATE(created_at)
CLUSTER BY evaluation_run_id, case_id;

CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${DATASET_ID}.dispatch_events` (
  event_id STRING NOT NULL,
  event_type STRING NOT NULL,
  occurred_at TIMESTAMP NOT NULL,
  ticket_id STRING,
  assignment_id STRING,
  approval_id STRING,
  idempotency_key STRING NOT NULL,
  payload JSON,
  success BOOL NOT NULL,
  error_type STRING
)
PARTITION BY DATE(occurred_at)
CLUSTER BY event_type, ticket_id, idempotency_key;

CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${DATASET_ID}.knowledge_chunks` (
  chunk_id STRING NOT NULL,
  document_id STRING NOT NULL,
  customer_id STRING,
  equipment_type STRING,
  document_type STRING NOT NULL,
  version STRING NOT NULL,
  effective_date DATE,
  text STRING NOT NULL,
  embedding ARRAY<FLOAT64>,
  metadata JSON,
  ingested_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(ingested_at)
CLUSTER BY document_type, customer_id, equipment_type;

