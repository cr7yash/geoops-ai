"""Deterministic key-free maps provider for local development and tests."""

from datetime import datetime
from math import asin, cos, radians, sin, sqrt

from geoops_api.domain.models import GeoPoint
from geoops_api.maps.models import (
    GeocodeNotFoundError,
    GeocodeResult,
    MapsProviderError,
    RouteElementStatus,
    RouteMatrixElement,
    RouteMatrixResult,
    RouteResult,
    RouteWaypoint,
)


class MockMapsProvider:
    """Estimate road routes from coordinates with stable failure fixtures."""

    name = "mock"
    _ROAD_DISTANCE_FACTOR = 1.22
    _AVERAGE_SPEED_KPH = 48.0

    def __init__(
        self,
        *,
        geocoding_index: dict[str, GeocodeResult] | None = None,
        failure_destinations: set[tuple[float, float]] | None = None,
    ) -> None:
        self._geocoding_index = {
            self._normalize_address(address): result
            for address, result in (geocoding_index or {}).items()
        }
        self._failure_destinations = failure_destinations or set()

    async def geocode(self, address: str) -> GeocodeResult:
        result = self._geocoding_index.get(self._normalize_address(address))
        if result is None:
            raise GeocodeNotFoundError(f"No deterministic geocode exists for {address!r}")
        return result

    async def compute_route(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        *,
        departure_time: datetime,
    ) -> RouteResult:
        if self._coordinate_key(destination) in self._failure_destinations:
            raise MapsProviderError("Simulated route provider failure")
        direct_distance = self._haversine_km(origin, destination)
        road_distance = round(direct_distance * self._ROAD_DISTANCE_FACTOR, 1)
        duration = round(max(5.0, road_distance / self._AVERAGE_SPEED_KPH * 60), 1)
        return RouteResult(
            provider=self.name,
            status=RouteElementStatus.OK,
            origin=origin,
            destination=destination,
            distance_km=road_distance,
            duration_minutes=duration,
            departure_time=departure_time,
            is_estimate=True,
        )

    async def compute_route_matrix(
        self,
        origins: list[RouteWaypoint],
        destinations: list[RouteWaypoint],
        *,
        departure_time: datetime,
    ) -> RouteMatrixResult:
        elements: list[RouteMatrixElement] = []
        for origin in origins:
            for destination in destinations:
                try:
                    route = await self.compute_route(
                        origin.location,
                        destination.location,
                        departure_time=departure_time,
                    )
                    elements.append(
                        RouteMatrixElement(
                            origin_id=origin.waypoint_id,
                            destination_id=destination.waypoint_id,
                            status=route.status,
                            distance_km=route.distance_km,
                            duration_minutes=route.duration_minutes,
                        )
                    )
                except MapsProviderError as error:
                    elements.append(
                        RouteMatrixElement(
                            origin_id=origin.waypoint_id,
                            destination_id=destination.waypoint_id,
                            status=RouteElementStatus.PROVIDER_ERROR,
                            error_message=str(error),
                        )
                    )
        return RouteMatrixResult(
            provider=self.name,
            departure_time=departure_time,
            is_estimate=True,
            elements=elements,
        )

    @staticmethod
    def _normalize_address(address: str) -> str:
        return " ".join(address.casefold().split())

    @staticmethod
    def _coordinate_key(point: GeoPoint) -> tuple[float, float]:
        return (round(point.latitude, 6), round(point.longitude, 6))

    @staticmethod
    def _haversine_km(origin: GeoPoint, destination: GeoPoint) -> float:
        earth_radius_km = 6371.0088
        origin_latitude = radians(origin.latitude)
        destination_latitude = radians(destination.latitude)
        latitude_delta = destination_latitude - origin_latitude
        longitude_delta = radians(destination.longitude - origin.longitude)
        value = sin(latitude_delta / 2) ** 2 + (
            cos(origin_latitude) * cos(destination_latitude) * sin(longitude_delta / 2) ** 2
        )
        return 2 * earth_radius_km * asin(sqrt(value))
