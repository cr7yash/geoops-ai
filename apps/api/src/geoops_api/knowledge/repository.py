"""Deterministic in-memory vector repository used by local development."""

from math import fsum

from geoops_api.knowledge.models import (
    IndexedKnowledgeChunk,
    KnowledgeFilters,
    KnowledgeSearchHit,
)


class InMemoryKnowledgeRepository:
    """Search normalized vectors while enforcing typed metadata filters."""

    def __init__(self) -> None:
        self._chunks: list[IndexedKnowledgeChunk] = []

    async def replace_all(self, chunks: list[IndexedKnowledgeChunk]) -> None:
        self._chunks = list(chunks)

    async def list_documents(self) -> list[IndexedKnowledgeChunk]:
        by_document: dict[str, IndexedKnowledgeChunk] = {}
        for chunk in self._chunks:
            by_document.setdefault(chunk.document_id, chunk)
        return sorted(by_document.values(), key=lambda item: (item.document_type, item.title))

    async def search(
        self,
        query_embedding: list[float],
        *,
        filters: KnowledgeFilters,
        limit: int,
        minimum_score: float,
    ) -> list[KnowledgeSearchHit]:
        candidates: list[KnowledgeSearchHit] = []
        for chunk in self._chunks:
            if not self._matches(chunk, filters):
                continue
            score = fsum(
                left * right for left, right in zip(query_embedding, chunk.embedding, strict=True)
            )
            if score < minimum_score:
                continue
            candidates.append(
                KnowledgeSearchHit(
                    chunk=chunk,
                    score=round(score, 6),
                    citation=self._citation(chunk),
                )
            )
        candidates.sort(key=lambda item: (-item.score, item.chunk.document_id, item.chunk.chunk_id))
        return candidates[:limit]

    @staticmethod
    def _matches(chunk: IndexedKnowledgeChunk, filters: KnowledgeFilters) -> bool:
        if filters.customer_id and chunk.customer_id != filters.customer_id:
            return False
        if filters.equipment_type and chunk.equipment_type != filters.equipment_type:
            return False
        if filters.document_type and chunk.document_type != filters.document_type:
            return False
        return not (
            filters.effective_on
            and chunk.effective_date
            and chunk.effective_date > filters.effective_on
        )

    @staticmethod
    def _citation(chunk: IndexedKnowledgeChunk) -> str:
        return f"[{chunk.title} v{chunk.version} — {chunk.section}]"
