"""Protocols that isolate document storage, embeddings, and retrieval."""

from typing import Protocol

from geoops_api.knowledge.models import (
    IndexedKnowledgeChunk,
    KnowledgeFilters,
    KnowledgeSearchHit,
    SourceDocument,
)


class DocumentStorage(Protocol):
    async def list_documents(self) -> list[SourceDocument]: ...


class EmbeddingProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


class KnowledgeRepository(Protocol):
    async def replace_all(self, chunks: list[IndexedKnowledgeChunk]) -> None: ...

    async def list_documents(self) -> list[IndexedKnowledgeChunk]: ...

    async def search(
        self,
        query_embedding: list[float],
        *,
        filters: KnowledgeFilters,
        limit: int,
        minimum_score: float,
    ) -> list[KnowledgeSearchHit]: ...
