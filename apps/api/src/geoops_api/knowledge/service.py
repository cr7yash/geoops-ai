"""Application service for ingestion and cited semantic retrieval."""

import asyncio

from geoops_api.knowledge.chunking import MarkdownChunker
from geoops_api.knowledge.interfaces import (
    DocumentStorage,
    EmbeddingProvider,
    KnowledgeRepository,
)
from geoops_api.knowledge.models import (
    IndexedKnowledgeChunk,
    IngestionReport,
    KnowledgeFilters,
    KnowledgeSearchHit,
)


class KnowledgeService:
    """Coordinate source loading, chunking, embeddings, and retrieval."""

    def __init__(
        self,
        storage: DocumentStorage,
        embedding_provider: EmbeddingProvider,
        repository: KnowledgeRepository,
        chunker: MarkdownChunker,
    ) -> None:
        self._storage = storage
        self._embedding_provider = embedding_provider
        self._repository = repository
        self._chunker = chunker
        self._ready = False
        self._ingestion_lock = asyncio.Lock()

    async def ingest(self) -> IngestionReport:
        async with self._ingestion_lock:
            return await self._ingest_unlocked()

    async def list_documents(self) -> list[IndexedKnowledgeChunk]:
        await self._ensure_ready()
        return await self._repository.list_documents()

    async def search(
        self,
        query: str,
        *,
        filters: KnowledgeFilters,
        limit: int,
        minimum_score: float,
    ) -> list[KnowledgeSearchHit]:
        await self._ensure_ready()
        embedding = await self._embedding_provider.embed_query(query)
        return await self._repository.search(
            embedding,
            filters=filters,
            limit=limit,
            minimum_score=minimum_score,
        )

    async def _ensure_ready(self) -> None:
        if self._ready:
            return
        async with self._ingestion_lock:
            if not self._ready:
                await self._ingest_unlocked()

    async def _ingest_unlocked(self) -> IngestionReport:
        documents = await self._storage.list_documents()
        raw_chunks = [chunk for document in documents for chunk in self._chunker.chunk(document)]
        embeddings = await self._embedding_provider.embed_documents(
            [f"{chunk.title}\n{chunk.section}\n{chunk.text}" for chunk in raw_chunks]
        )
        chunks = [
            chunk.model_copy(update={"embedding": embedding})
            for chunk, embedding in zip(raw_chunks, embeddings, strict=True)
        ]
        await self._repository.replace_all(chunks)
        self._ready = True
        return IngestionReport(
            document_count=len(documents),
            chunk_count=len(chunks),
            embedding_provider=self._embedding_provider.name,
            embedding_dimensions=self._embedding_provider.dimensions,
        )
