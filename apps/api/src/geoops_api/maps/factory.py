"""Select and configure the maps provider from validated settings."""

from geoops_api.config import Settings
from geoops_api.domain.models import SeedDataset
from geoops_api.maps.google import GoogleMapsProvider
from geoops_api.maps.interfaces import MapsProvider
from geoops_api.maps.mock import MockMapsProvider
from geoops_api.maps.models import GeocodeResult


def build_maps_provider(settings: Settings, dataset: SeedDataset) -> MapsProvider:
    if settings.maps_provider == "google":
        assert settings.google_maps_api_key is not None
        return GoogleMapsProvider(
            settings.google_maps_api_key.get_secret_value(),
            timeout_seconds=settings.maps_timeout_seconds,
        )

    geocoding_index: dict[str, GeocodeResult] = {}
    failure_destinations: set[tuple[float, float]] = set()
    for site in dataset.sites:
        if site.location is None:
            continue
        address = f"{site.address}, {site.city}, {site.state} {site.postal_code}"
        geocoding_index[address] = GeocodeResult(
            provider="mock",
            formatted_address=address,
            location=site.location,
            place_id=f"mock:{site.site_id}",
            precision="seed",
        )
        if site.routing_mode == "simulate_failure":
            failure_destinations.add(
                (round(site.location.latitude, 6), round(site.location.longitude, 6))
            )
    return MockMapsProvider(
        geocoding_index=geocoding_index,
        failure_destinations=failure_destinations,
    )
