# BigQuery schema

`001_core.sql` defines the analytical schema using BigQuery-native types, time partitioning for event/history tables, and clustering around common access paths. `002_knowledge_vector_index.sql` adds an IVF cosine index over knowledge embeddings, while `knowledge_vector_search.sql` documents the parameterized, metadata-filtered `VECTOR_SEARCH` contract used by the cloud adapter.

The SQL is intentionally deployment-neutral. Substitute `PROJECT_ID` and `DATASET_ID` through the deployment pipeline before execution. BigQuery is not required for local mode; structured records and knowledge retrieval both have deterministic local adapters behind provider-neutral boundaries.
