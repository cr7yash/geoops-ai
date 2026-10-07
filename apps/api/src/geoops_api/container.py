"""Dependency container for provider-neutral application services."""

from dataclasses import dataclass

from geoops_api.config import Settings
from geoops_api.knowledge.chunking import MarkdownChunker
from geoops_api.knowledge.embeddings import DeterministicEmbeddingProvider
from geoops_api.knowledge.repository import InMemoryKnowledgeRepository
from geoops_api.knowledge.service import KnowledgeService
from geoops_api.knowledge.storage import FilesystemDocumentStorage
from geoops_api.maps.factory import build_maps_provider
from geoops_api.maps.interfaces import MapsProvider
from geoops_api.repositories.local import JsonCatalogRepository
from geoops_api.services.catalog import CatalogService
from geoops_api.services.dispatch import DispatchService


@dataclass(frozen=True)
class ApplicationContainer:
    catalog_repository: JsonCatalogRepository
    catalog_service: CatalogService
    dispatch_service: DispatchService
    maps_provider: MapsProvider
    knowledge_service: KnowledgeService


def build_container(settings: Settings) -> ApplicationContainer:
    repository = JsonCatalogRepository(settings.seed_data_path)
    maps_provider = build_maps_provider(settings, repository.dataset)
    knowledge_service = KnowledgeService(
        storage=FilesystemDocumentStorage(settings.knowledge_documents_path),
        embedding_provider=DeterministicEmbeddingProvider(settings.embedding_dimensions),
        repository=InMemoryKnowledgeRepository(),
        chunker=MarkdownChunker(
            maximum_characters=settings.knowledge_chunk_size,
            overlap_characters=settings.knowledge_chunk_overlap,
        ),
    )
    return ApplicationContainer(
        catalog_repository=repository,
        catalog_service=CatalogService(repository),
        dispatch_service=DispatchService(repository, maps_provider),
        maps_provider=maps_provider,
        knowledge_service=knowledge_service,
    )
