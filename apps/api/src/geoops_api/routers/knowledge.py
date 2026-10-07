"""Enterprise knowledge ingestion and cited semantic search endpoints."""

from fastapi import APIRouter, Request

from geoops_api.container import ApplicationContainer
from geoops_api.knowledge.models import KnowledgeFilters
from geoops_api.schemas.knowledge import (
    KnowledgeDocumentListResponse,
    KnowledgeDocumentSummary,
    KnowledgeIngestionResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSource,
)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get(
    "/documents",
    response_model=KnowledgeDocumentListResponse,
    summary="List indexed knowledge documents",
)
async def list_documents(request: Request) -> KnowledgeDocumentListResponse:
    container: ApplicationContainer = request.app.state.container
    documents = await container.knowledge_service.list_documents()
    items = [
        KnowledgeDocumentSummary(
            document_id=item.document_id,
            title=item.title,
            document_type=item.document_type,
            version=item.version,
            effective_date=item.effective_date,
            customer_id=item.customer_id,
            equipment_type=item.equipment_type,
            storage_uri=item.storage_uri,
        )
        for item in documents
    ]
    return KnowledgeDocumentListResponse(items=items, total=len(items))


@router.post(
    "/search",
    response_model=KnowledgeSearchResponse,
    summary="Search knowledge with metadata filters and citations",
)
async def search_knowledge(
    payload: KnowledgeSearchRequest, request: Request
) -> KnowledgeSearchResponse:
    container: ApplicationContainer = request.app.state.container
    hits = await container.knowledge_service.search(
        payload.query,
        filters=KnowledgeFilters(
            customer_id=payload.customer_id,
            equipment_type=payload.equipment_type,
            document_type=payload.document_type,
            effective_on=payload.effective_on,
        ),
        limit=payload.limit,
        minimum_score=payload.minimum_score,
    )
    sources = [
        KnowledgeSource(
            rank=rank,
            score=hit.score,
            citation=hit.citation,
            chunk_id=hit.chunk.chunk_id,
            document_id=hit.chunk.document_id,
            title=hit.chunk.title,
            document_type=hit.chunk.document_type,
            version=hit.chunk.version,
            effective_date=hit.chunk.effective_date,
            customer_id=hit.chunk.customer_id,
            equipment_type=hit.chunk.equipment_type,
            section=hit.chunk.section,
            excerpt=hit.chunk.text,
            storage_uri=hit.chunk.storage_uri,
        )
        for rank, hit in enumerate(hits, 1)
    ]
    return KnowledgeSearchResponse(
        query=payload.query,
        result_count=len(sources),
        sources=sources,
    )


@router.post(
    "/ingest",
    response_model=KnowledgeIngestionResponse,
    summary="Rebuild the deterministic local knowledge index",
)
async def ingest_knowledge(request: Request) -> KnowledgeIngestionResponse:
    container: ApplicationContainer = request.app.state.container
    report = await container.knowledge_service.ingest()
    return KnowledgeIngestionResponse.model_validate(report.model_dump())
