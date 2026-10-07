"""Dependency container for provider-neutral application services."""

from dataclasses import dataclass

from geoops_api.config import Settings
from geoops_api.repositories.local import JsonCatalogRepository
from geoops_api.services.catalog import CatalogService
from geoops_api.services.dispatch import DispatchService


@dataclass(frozen=True)
class ApplicationContainer:
    catalog_repository: JsonCatalogRepository
    catalog_service: CatalogService
    dispatch_service: DispatchService


def build_container(settings: Settings) -> ApplicationContainer:
    repository = JsonCatalogRepository(settings.seed_data_path)
    return ApplicationContainer(
        catalog_repository=repository,
        catalog_service=CatalogService(repository),
        dispatch_service=DispatchService(repository),
    )
