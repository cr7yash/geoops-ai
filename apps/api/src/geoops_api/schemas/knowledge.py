"""Public contracts for knowledge ingestion and cited retrieval."""

from datetime import date

from pydantic import Field

from geoops_api.knowledge.models import DocumentType
from geoops_api.schemas.catalog import ApiModel


class KnowledgeSearchRequest(ApiModel):
    query: str = Field(min_length=3, max_length=500)
    customer_id: str | None = Field(default=None, max_length=50)
    equipment_type: str | None = Field(default=None, max_length=100)
    document_type: DocumentType | None = None
    effective_on: date | None = None
    limit: int = Field(default=5, ge=1, le=20)
    minimum_score: float = Field(default=0.05, ge=-1, le=1)


class KnowledgeDocumentSummary(ApiModel):
    document_id: str
    title: str
    document_type: DocumentType
    version: str
    effective_date: date | None
    customer_id: str | None
    equipment_type: str | None
    storage_uri: str


class KnowledgeDocumentListResponse(ApiModel):
    items: list[KnowledgeDocumentSummary]
    total: int = Field(ge=0)


class KnowledgeSource(ApiModel):
    rank: int = Field(ge=1)
    score: float = Field(ge=-1, le=1)
    citation: str
    chunk_id: str
    document_id: str
    title: str
    document_type: DocumentType
    version: str
    effective_date: date | None
    customer_id: str | None
    equipment_type: str | None
    section: str
    excerpt: str
    storage_uri: str


class KnowledgeSearchResponse(ApiModel):
    query: str
    result_count: int = Field(ge=0)
    sources: list[KnowledgeSource]


class KnowledgeIngestionResponse(ApiModel):
    document_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    embedding_provider: str
    embedding_dimensions: int = Field(gt=0)
