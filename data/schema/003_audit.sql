CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${DATASET_ID}.audit_records` (
  collection STRING NOT NULL,
  record_id STRING NOT NULL,
  recorded_at TIMESTAMP NOT NULL,
  payload JSON NOT NULL
)
PARTITION BY DATE(recorded_at)
CLUSTER BY collection, record_id;

CREATE OR REPLACE VIEW `${PROJECT_ID}.${DATASET_ID}.evaluation_history` AS
SELECT record_id AS evaluation_run_id, recorded_at,
       JSON_VALUE(payload, '$.model') AS model,
       JSON_VALUE(payload, '$.dataset_sha256') AS dataset_sha256,
       JSON_QUERY(payload, '$.metrics') AS metrics,
       JSON_QUERY(payload, '$.results') AS results
FROM `${PROJECT_ID}.${DATASET_ID}.audit_records`
WHERE collection = 'evaluations';
