"""Verify the data sent to BigQuery matches the tables provisioned by Terraform."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest
from google.auth.credentials import AnonymousCredentials
from google.cloud import bigquery

from geoops_api import bootstrap
from geoops_api.cloud_knowledge import BigQueryKnowledgeRepository
from geoops_api.knowledge.models import DocumentType, IndexedKnowledgeChunk, KnowledgeFilters

SCHEMAS_PATH = Path(__file__).resolve().parents[3] / "infrastructure/terraform/tables.json"


@pytest.fixture
def bigquery_loads(monkeypatch: pytest.MonkeyPatch):
    schemas = json.loads(SCHEMAS_PATH.read_text())
    client = bigquery.Client(project="test-project", credentials=AnonymousCredentials())
    loads = {}

    def capture_load(file, destination, *, job_config, **kwargs):
        rows = [json.loads(line) for line in file]
        loads[destination.table_id] = (rows, job_config)
        return Mock()

    monkeypatch.setattr(client, "load_table_from_file", capture_load)
    monkeypatch.setattr(bigquery, "Client", lambda **kwargs: client)
    return client, schemas, loads


@pytest.mark.anyio
async def test_knowledge_load_preserves_partition_and_reads_native_json(bigquery_loads) -> None:
    client, schemas, loads = bigquery_loads
    chunk = IndexedKnowledgeChunk(
        chunk_id="manual-1:0",
        document_id="manual-1",
        title="Compressor manual",
        document_type=DocumentType.MANUAL,
        version="1",
        storage_uri="manuals/compressor.md",
        section="Diagnostics",
        text="Check the pressure sensor.",
        embedding=[1.0, 0.0],
    )
    repository = BigQueryKnowledgeRepository("test-project", "geoops")
    await repository.replace_all([chunk])

    rows, config = loads["knowledge_chunks"]
    (row,) = rows
    partition = schemas["knowledge_chunks"]["partition"]
    assert datetime.fromisoformat(row[partition]).tzinfo == UTC
    assert config.autodetect is False
    assert config.create_disposition == bigquery.CreateDisposition.CREATE_NEVER
    assert config.write_disposition == bigquery.WriteDisposition.WRITE_TRUNCATE_DATA
    assert isinstance(row["metadata"], dict)

    # The BigQuery client returns a Python object for a native JSON field.
    client.query = Mock(return_value=Mock(result=Mock(return_value=[{**row, "score": 1.0}])))
    assert await repository.list_documents() == [chunk]
    hits = await repository.search(
        chunk.embedding, filters=KnowledgeFilters(), limit=1, minimum_score=0.0
    )
    assert [hit.chunk for hit in hits] == [chunk]


def test_catalog_bootstrap_uses_canonical_schema_to_restore_types(
    bigquery_loads, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, schemas, loads = bigquery_loads
    monkeypatch.setattr(sys, "argv", ["bootstrap", "--replace"])
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("BIGQUERY_DATASET", "geoops")

    bootstrap.main()

    assert len(loads) == 8
    for table, (rows, config) in loads.items():
        assert config.autodetect is False
        assert config.create_disposition == bigquery.CreateDisposition.CREATE_NEVER
        assert [field.to_api_repr() for field in config.schema] == schemas[table]["fields"]
        assert (config.time_partitioning.field if config.time_partitioning else None) == schemas[
            table
        ]["partition"]
        assert (config.clustering_fields or []) == schemas[table]["clustering"]
        required = {field.name for field in config.schema if field.mode == "REQUIRED"}
        assert all(all(row.get(field) is not None for field in required) for row in rows)
    assert any(row["location"].startswith("POINT(") for row in loads["sites"][0] if row["location"])
    assert isinstance(loads["sla_events"][0][0]["metadata"], dict)
