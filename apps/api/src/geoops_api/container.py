"""Dependency container for provider-neutral application services."""

from dataclasses import dataclass
from datetime import timedelta

from geoops_api.agent.factory import build_agent_runtime
from geoops_api.agent.runtime import AgentRuntime
from geoops_api.agent.tools import AgentToolRegistry
from geoops_api.analytics import AnalyticsStore, BigQueryAnalyticsStore, LocalAnalyticsStore
from geoops_api.approvals.factory import build_approval_repository
from geoops_api.approvals.service import ApprovalService
from geoops_api.cloud_knowledge import (
    BigQueryKnowledgeRepository,
    GoogleCloudDocumentStorage,
    GoogleEmbeddingProvider,
)
from geoops_api.config import Settings
from geoops_api.evaluation import EvaluationService
from geoops_api.events import EventBus, GooglePubSubEventBus, InMemoryEventBus
from geoops_api.knowledge.chunking import MarkdownChunker
from geoops_api.knowledge.embeddings import DeterministicEmbeddingProvider
from geoops_api.knowledge.interfaces import DocumentStorage, EmbeddingProvider, KnowledgeRepository
from geoops_api.knowledge.repository import InMemoryKnowledgeRepository
from geoops_api.knowledge.service import KnowledgeService
from geoops_api.knowledge.storage import FilesystemDocumentStorage
from geoops_api.maps.factory import build_maps_provider
from geoops_api.maps.interfaces import MapsProvider
from geoops_api.repositories.bigquery import BigQueryCatalogRepository
from geoops_api.repositories.local import JsonCatalogRepository
from geoops_api.services.catalog import CatalogService
from geoops_api.services.dispatch import DispatchService
from geoops_api.telemetry import AnalyticsRelay, RecordedAgentRuntime
from geoops_api.worker import DispatchWorker, OutboxRelay
from geoops_api.workflow import WorkflowRepository


@dataclass(frozen=True)
class ApplicationContainer:
    catalog_repository: JsonCatalogRepository
    catalog_service: CatalogService
    dispatch_service: DispatchService
    maps_provider: MapsProvider
    knowledge_service: KnowledgeService
    approval_repository: WorkflowRepository
    approval_service: ApprovalService
    agent_runtime: AgentRuntime
    event_bus: EventBus
    dispatch_worker: DispatchWorker
    outbox_relay: OutboxRelay
    evaluation_service: EvaluationService
    analytics_relay: AnalyticsRelay


def build_container(settings: Settings) -> ApplicationContainer:
    approval_repository = build_approval_repository(settings)
    repository = JsonCatalogRepository(settings.seed_data_path, approval_repository)
    if settings.catalog_provider == "bigquery":
        repository = BigQueryCatalogRepository(settings.seed_data_path, approval_repository)
        repository.configure(settings.google_cloud_project or "", settings.bigquery_dataset)
    maps_provider = build_maps_provider(settings, repository.dataset)
    documents: DocumentStorage = FilesystemDocumentStorage(settings.knowledge_documents_path)
    embeddings: EmbeddingProvider = DeterministicEmbeddingProvider(settings.embedding_dimensions)
    vectors: KnowledgeRepository = InMemoryKnowledgeRepository()
    if settings.document_provider == "gcs":
        documents = GoogleCloudDocumentStorage(
            settings.google_cloud_project or "", settings.documents_bucket or ""
        )
    if settings.embedding_provider == "google":
        embeddings = GoogleEmbeddingProvider(settings)
    if settings.vector_provider == "bigquery":
        vectors = BigQueryKnowledgeRepository(
            settings.google_cloud_project or "", settings.bigquery_dataset
        )
    knowledge_service = KnowledgeService(
        storage=documents,
        embedding_provider=embeddings,
        repository=vectors,
        preindexed=settings.vector_provider == "bigquery",
        chunker=MarkdownChunker(
            maximum_characters=settings.knowledge_chunk_size,
            overlap_characters=settings.knowledge_chunk_overlap,
        ),
    )
    catalog_service = CatalogService(repository)
    dispatch_service = DispatchService(repository, maps_provider)
    approval_service = ApprovalService(
        repository=approval_repository,
        catalog_service=catalog_service,
        dispatch_service=dispatch_service,
        ttl=timedelta(minutes=settings.approval_ttl_minutes),
    )
    agent_registry = AgentToolRegistry(
        catalog_service=catalog_service,
        dispatch_service=dispatch_service,
        knowledge_service=knowledge_service,
        approval_service=approval_service,
    )
    dispatch_worker = DispatchWorker(approval_repository, catalog_service, dispatch_service)
    event_bus: EventBus
    if settings.event_bus == "pubsub":
        event_bus = GooglePubSubEventBus(settings.google_cloud_project or "", settings.pubsub_topic)
    else:
        local_bus = InMemoryEventBus()
        local_bus.subscribe(dispatch_worker.consume)
        event_bus = local_bus
    analytics: AnalyticsStore = LocalAnalyticsStore(approval_repository.store)
    if settings.analytics_provider == "bigquery":
        analytics = BigQueryAnalyticsStore(
            settings.google_cloud_project or "", settings.bigquery_dataset
        )
    return ApplicationContainer(
        catalog_repository=repository,
        catalog_service=catalog_service,
        dispatch_service=dispatch_service,
        maps_provider=maps_provider,
        knowledge_service=knowledge_service,
        approval_repository=approval_repository,
        approval_service=approval_service,
        agent_runtime=RecordedAgentRuntime(
            build_agent_runtime(settings, agent_registry),
            approval_repository.store,
            settings.agent_timeout_seconds,
            settings.model_input_usd_per_million,
            settings.model_output_usd_per_million,
        ),
        event_bus=event_bus,
        dispatch_worker=dispatch_worker,
        outbox_relay=OutboxRelay(approval_repository, event_bus),
        evaluation_service=EvaluationService(settings, approval_repository.store),
        analytics_relay=AnalyticsRelay(approval_repository.store, analytics),
    )
