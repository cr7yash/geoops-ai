"""Knowledge ingestion, deterministic embeddings, filters, and API contracts."""

from math import sqrt
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from geoops_api.config import Settings
from geoops_api.knowledge.chunking import MarkdownChunker
from geoops_api.knowledge.embeddings import DeterministicEmbeddingProvider
from geoops_api.knowledge.storage import DocumentFormatError, FilesystemDocumentStorage
from geoops_api.main import create_app


def make_client(**overrides: object) -> TestClient:
    settings = Settings(_env_file=None, **overrides)  # type: ignore[arg-type]
    return TestClient(create_app(settings))


@pytest.mark.anyio
async def test_local_embeddings_are_normalized_and_repeatable() -> None:
    provider = DeterministicEmbeddingProvider(dimensions=32)

    first = await provider.embed_query("compressor pressure loss")
    second = await provider.embed_query("compressor pressure loss")

    assert first == second
    assert len(first) == 32
    assert sqrt(sum(value * value for value in first)) == pytest.approx(1.0)


@pytest.mark.anyio
async def test_filesystem_storage_and_chunk_ids_are_deterministic() -> None:
    storage = FilesystemDocumentStorage(Settings(_env_file=None).knowledge_documents_path)
    documents = await storage.list_documents()
    chunker = MarkdownChunker(maximum_characters=900, overlap_characters=120)

    first = [chunk for document in documents for chunk in chunker.chunk(document)]
    second = [chunk for document in documents for chunk in chunker.chunk(document)]

    assert len(documents) == 8
    assert len(first) == 24
    assert [item.chunk_id for item in first] == [item.chunk_id for item in second]
    assert {item.document_type for item in first} == {
        "contract",
        "manual",
        "service_report",
        "incident_history",
        "policy",
    }


@pytest.mark.anyio
async def test_storage_rejects_missing_front_matter(tmp_path: Path) -> None:
    (tmp_path / "invalid.md").write_text("# No metadata\n\nText", encoding="utf-8")
    storage = FilesystemDocumentStorage(tmp_path)

    with pytest.raises(DocumentFormatError, match="must start"):
        await storage.list_documents()


def test_ingestion_and_document_catalog_contracts() -> None:
    with make_client() as client:
        ingested = client.post("/api/knowledge/ingest")
        documents = client.get("/api/knowledge/documents")

    assert ingested.status_code == 200
    assert ingested.json() == {
        "document_count": 8,
        "chunk_count": 24,
        "embedding_provider": "deterministic-hashing-v1",
        "embedding_dimensions": 256,
    }
    assert documents.status_code == 200
    assert documents.json()["total"] == 8
    assert all(item["storage_uri"].endswith(".md") for item in documents.json()["items"])


def test_search_returns_ranked_citations_and_honors_metadata_filters() -> None:
    payload = {
        "query": "What should be checked first for compressor pressure loss?",
        "equipment_type": "compressor",
        "document_type": "manual",
        "limit": 5,
        "minimum_score": -1,
    }
    with make_client() as client:
        first = client.post("/api/knowledge/search", json=payload)
        second = client.post("/api/knowledge/search", json=payload)

    assert first.status_code == 200
    assert first.json() == second.json()
    body = first.json()
    assert body["result_count"] > 0
    assert body["sources"][0]["title"] == "Compressor Field Service Manual"
    assert body["sources"][0]["section"] == "Initial diagnostic sequence"
    assert [source["rank"] for source in body["sources"]] == list(
        range(1, body["result_count"] + 1)
    )
    assert all(source["equipment_type"] == "compressor" for source in body["sources"])
    assert all(source["document_type"] == "manual" for source in body["sources"])
    assert all(source["citation"].startswith("[") for source in body["sources"])
    assert any("pressure" in source["excerpt"].casefold() for source in body["sources"])


def test_customer_filter_and_no_result_state_are_explicit() -> None:
    with make_client() as client:
        customer = client.post(
            "/api/knowledge/search",
            json={
                "query": "critical incident response target",
                "customer_id": "C-002",
                "minimum_score": -1,
            },
        )
        empty = client.post(
            "/api/knowledge/search",
            json={
                "query": "compressor",
                "customer_id": "C-999",
                "minimum_score": -1,
            },
        )

    assert customer.status_code == 200
    assert customer.json()["result_count"] > 0
    assert all(source["customer_id"] == "C-002" for source in customer.json()["sources"])
    assert empty.status_code == 200
    assert empty.json() == {"query": "compressor", "result_count": 0, "sources": []}


def test_search_request_validation_rejects_unknown_document_type() -> None:
    with make_client() as client:
        response = client.post(
            "/api/knowledge/search",
            json={"query": "compressor", "document_type": "memo"},
        )

    assert response.status_code == 422
