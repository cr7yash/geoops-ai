"""Dependency container for provider-neutral application services."""

from dataclasses import dataclass

from geoops_api.config import Settings
from geoops_api.repositories.local import JsonCatalogRepository
from geoops_api.services.catalog import CatalogService


@dataclass(frozen=True)
class ApplicationContainer:
    catalog_repository: JsonCatalogRepository
    catalog_service: CatalogService


def build_container(settings: Settings) -> ApplicationContainer:
    repository = JsonCatalogRepository(settings.seed_data_path)
    return ApplicationContainer(
        catalog_repository=repository,
        catalog_service=CatalogService(repository),
    )
