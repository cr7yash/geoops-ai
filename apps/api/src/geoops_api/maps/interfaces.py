"""Provider boundary for geocoding and route calculations."""

from datetime import datetime
from typing import Protocol

from geoops_api.domain.models import GeoPoint
from geoops_api.maps.models import (
    GeocodeResult,
    RouteMatrixResult,
    RouteResult,
    RouteWaypoint,
)


class MapsProvider(Protocol):
    @property
    def name(self) -> str: ...

    async def geocode(self, address: str) -> GeocodeResult: ...

    async def compute_route(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        *,
        departure_time: datetime,
    ) -> RouteResult: ...

    async def compute_route_matrix(
        self,
        origins: list[RouteWaypoint],
        destinations: list[RouteWaypoint],
        *,
        departure_time: datetime,
    ) -> RouteMatrixResult: ...
