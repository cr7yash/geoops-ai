"""GCS documents, Google embeddings, and BigQuery vector retrieval."""

import asyncio
import json
from pathlib import Path

import google.cloud.storage as storage  # type: ignore[import-untyped]
from google import genai
from google.cloud import bigquery
from google.genai import types

from geoops_api.config import Settings
from geoops_api.knowledge.models import (
    IndexedKnowledgeChunk,
    KnowledgeFilters,
    KnowledgeSearchHit,
    SourceDocument,
)
from geoops_api.knowledge.repository import InMemoryKnowledgeRepository
from geoops_api.knowledge.storage import FilesystemDocumentStorage


class GoogleCloudDocumentStorage:
    def __init__(self, project: str, bucket: str) -> None:
        self._client = storage.Client(project=project)
        self._bucket = bucket

    async def list_documents(self) -> list[SourceDocument]:
        def load() -> list[SourceDocument]:
            parser = FilesystemDocumentStorage(Path("."))
            documents = [
                parser.parse_text(blob.download_as_text(), blob.name)
                for blob in self._client.list_blobs(self._bucket)
                if blob.name.endswith(".md")
            ]
            if len({item.document_id for item in documents}) != len(documents):
                raise ValueError("Knowledge document IDs must be unique")
            return documents

        return await asyncio.to_thread(load)


class GoogleEmbeddingProvider:
    def __init__(self, settings: Settings) -> None:
        self.name = settings.embedding_model
        self.dimensions = settings.embedding_dimensions
        self._client = genai.Client(
            api_key=settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None,
            vertexai=settings.model_provider == "vertex_ai",
            project=settings.google_cloud_project
            if settings.model_provider == "vertex_ai"
            else None,
            location=settings.google_cloud_location
            if settings.model_provider == "vertex_ai"
            else None,
        )

    async def _embed(self, texts: list[str], task: str) -> list[list[float]]:
        response = await self._client.aio.models.embed_content(
            model=self.name,
            contents=texts,
            config=types.EmbedContentConfig(task_type=task, output_dimensionality=self.dimensions),
        )
        return [item.values or [] for item in response.embeddings or []]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for start in range(0, len(texts), 50):
            results.extend(await self._embed(texts[start : start + 50], "RETRIEVAL_DOCUMENT"))
        return results

    async def embed_query(self, text: str) -> list[float]:
        return (await self._embed([text], "RETRIEVAL_QUERY"))[0]


class BigQueryKnowledgeRepository:
    def __init__(self, project: str, dataset: str) -> None:
        self._client = bigquery.Client(project=project)
        self._table = f"{project}.{dataset}.knowledge_chunks"

    async def replace_all(self, chunks: list[IndexedKnowledgeChunk]) -> None:
        rows = [
            {
                "chunk_id": item.chunk_id,
                "document_id": item.document_id,
                "customer_id": item.customer_id,
                "equipment_type": item.equipment_type,
                "document_type": item.document_type.value,
                "version": item.version,
                "effective_date": str(item.effective_date) if item.effective_date else None,
                "text": item.text,
                "embedding": item.embedding,
                "metadata": json.dumps(item.model_dump(mode="json")),
            }
            for item in chunks
        ]
        config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
        await asyncio.to_thread(
            lambda: self._client.load_table_from_json(rows, self._table, job_config=config).result(
                timeout=120
            )
        )

    async def list_documents(self) -> list[IndexedKnowledgeChunk]:
        sql = (
            f"SELECT metadata FROM `{self._table}` QUALIFY "
            "ROW_NUMBER() OVER(PARTITION BY document_id ORDER BY chunk_id) = 1"
        )
        rows = await asyncio.to_thread(lambda: list(self._client.query(sql).result(timeout=60)))
        return [IndexedKnowledgeChunk.model_validate_json(row["metadata"]) for row in rows]

    async def search(
        self,
        query_embedding: list[float],
        *,
        filters: KnowledgeFilters,
        limit: int,
        minimum_score: float,
    ) -> list[KnowledgeSearchHit]:
        sql = f"""SELECT base.metadata, 1 - distance AS score FROM VECTOR_SEARCH(
            (SELECT * FROM `{self._table}` WHERE
             (@customer IS NULL OR customer_id = @customer OR (@global AND customer_id IS NULL))
             AND (@equipment IS NULL OR equipment_type = @equipment)
             AND (@doctype IS NULL OR document_type = @doctype)
             AND (@effective IS NULL OR effective_date IS NULL OR effective_date <= @effective)),
            'embedding', (SELECT @embedding AS embedding), top_k => @limit,
            distance_type => 'COSINE', options => '{{"use_brute_force":true}}')
            WHERE 1 - distance >= @minimum ORDER BY distance, base.chunk_id"""
        config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("embedding", "FLOAT64", query_embedding),
                bigquery.ScalarQueryParameter("customer", "STRING", filters.customer_id),
                bigquery.ScalarQueryParameter("global", "BOOL", filters.include_global),
                bigquery.ScalarQueryParameter("equipment", "STRING", filters.equipment_type),
                bigquery.ScalarQueryParameter("doctype", "STRING", filters.document_type),
                bigquery.ScalarQueryParameter("effective", "DATE", filters.effective_on),
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
                bigquery.ScalarQueryParameter("minimum", "FLOAT64", minimum_score),
            ],
            maximum_bytes_billed=100_000_000,
        )
        rows = await asyncio.to_thread(
            lambda: list(self._client.query(sql, job_config=config).result(timeout=60))
        )
        results: list[KnowledgeSearchHit] = []
        for row in rows:
            chunk = IndexedKnowledgeChunk.model_validate_json(row["metadata"])
            results.append(
                KnowledgeSearchHit(
                    chunk=chunk,
                    score=max(-1, min(1, row["score"])),
                    citation=InMemoryKnowledgeRepository._citation(chunk),
                )
            )
        return results
