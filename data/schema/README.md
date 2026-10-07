# BigQuery schema

`001_core.sql` defines the Phase 2 analytical schema using BigQuery-native types, time partitioning for event/history tables, and clustering around common access paths.

The SQL is intentionally deployment-neutral. Substitute `PROJECT_ID` and `DATASET_ID` through the deployment pipeline before execution. BigQuery is not required for local mode; the API reads the deterministic JSON snapshot through the same repository boundary that a future BigQuery adapter will implement.

