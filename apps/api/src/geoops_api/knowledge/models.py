"""Typed values shared by ingestion, retrieval, and API adapters."""

from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DocumentType(StrEnum):
    CONTRACT = "contract"
    MANUAL = "manual"
    SERVICE_REPORT = "service_report"
    INCIDENT_HISTORY = "incident_history"
    POLICY = "policy"


class SourceDocument(KnowledgeModel):
    document_id: str
    title: str
    document_type: DocumentType
    version: str
    effective_date: date | None = None
    customer_id: str | None = None
    equipment_type: str | None = None
    storage_uri: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class IndexedKnowledgeChunk(KnowledgeModel):
    chunk_id: str
    document_id: str
    title: str
    document_type: DocumentType
    version: str
    effective_date: date | None = None
    customer_id: str | None = None
    equipment_type: str | None = None
    storage_uri: str
    section: str
    text: str
    embedding: list[float]
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeFilters(KnowledgeModel):
    customer_id: str | None = None
    equipment_type: str | None = None
    document_type: DocumentType | None = None
    effective_on: date | None = None


class KnowledgeSearchHit(KnowledgeModel):
    chunk: IndexedKnowledgeChunk
    score: float = Field(ge=-1, le=1)
    citation: str


class IngestionReport(KnowledgeModel):
    document_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    embedding_provider: str
    embedding_dimensions: int = Field(gt=0)
