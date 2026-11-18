"""Historical records in local documents or idempotent BigQuery MERGE operations."""

import asyncio
import json
from typing import Any, Protocol

from google.cloud import bigquery

from geoops_api.state import DocumentStore


class AnalyticsStore(Protocol):
    async def save(self, collection: str, record_id: str, record: dict[str, Any]) -> None: ...


class LocalAnalyticsStore:
    def __init__(self, store: DocumentStore) -> None:
        self.store = store

    async def save(self, collection: str, record_id: str, record: dict[str, Any]) -> None:
        await self.store.transact([], lambda _: {f"audit/{collection}-{record_id}": record})


class BigQueryAnalyticsStore:
    def __init__(self, project: str, dataset: str) -> None:
        self._client = bigquery.Client(project=project)
        self._table = f"{project}.{dataset}.audit_records"

    async def save(self, collection: str, record_id: str, record: dict[str, Any]) -> None:
        sql = f"""MERGE `{self._table}` target
            USING (SELECT @collection AS collection, @id AS record_id) source
            ON target.collection = source.collection AND target.record_id = source.record_id
            WHEN NOT MATCHED THEN INSERT (collection, record_id, recorded_at, payload)
            VALUES (@collection, @id, CURRENT_TIMESTAMP(), PARSE_JSON(@payload))"""
        config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("collection", "STRING", collection),
                bigquery.ScalarQueryParameter("id", "STRING", record_id),
                bigquery.ScalarQueryParameter("payload", "STRING", json.dumps(record)),
            ],
            maximum_bytes_billed=100_000_000,
        )
        await asyncio.to_thread(
            lambda: self._client.query(sql, job_config=config).result(timeout=60)
        )
        if collection == "evaluations":
            table = self._table.removesuffix("audit_records") + "eval_results"
            sql = f"""MERGE `{table}` target USING (
                SELECT CONCAT(@id, ':', JSON_VALUE(item, '$.case_id')) AS evaluation_result_id,
                       @id AS evaluation_run_id, JSON_VALUE(item, '$.case_id') AS case_id,
                       CAST(JSON_VALUE(PARSE_JSON(@payload), '$.created_at') AS TIMESTAMP)
                           AS created_at,
                       CAST(JSON_VALUE(item, '$.task_success') AS BOOL) AS task_success,
                       CAST(JSON_VALUE(item, '$.tool_selection_accuracy') AS FLOAT64)
                           AS tool_selection_accuracy,
                       CAST(JSON_VALUE(item, '$.tool_argument_accuracy') AS FLOAT64)
                           AS tool_argument_accuracy,
                       CAST(JSON_VALUE(item, '$.retrieval_recall') AS FLOAT64) AS retrieval_recall,
                       CAST(JSON_VALUE(item, '$.citation_correctness') AS FLOAT64)
                           AS citation_correctness,
                       CAST(JSON_VALUE(item, '$.policy_compliance') AS FLOAT64)
                           AS policy_compliance,
                       CAST(JSON_VALUE(item, '$.latency_ms') AS FLOAT64) AS latency_ms,
                       CAST(JSON_VALUE(item, '$.token_usage') AS INT64) AS token_usage,
                       CAST(JSON_VALUE(item, '$.estimated_cost_usd') AS NUMERIC)
                           AS estimated_cost_usd,
                       item AS metrics
                FROM UNNEST(JSON_QUERY_ARRAY(PARSE_JSON(@payload), '$.results')) item
            ) source ON target.evaluation_result_id = source.evaluation_result_id
            WHEN NOT MATCHED THEN INSERT ROW"""
            await asyncio.to_thread(
                lambda: self._client.query(sql, job_config=config).result(timeout=60)
            )
