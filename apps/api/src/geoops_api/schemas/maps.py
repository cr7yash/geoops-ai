"""Validated request bodies for maps operations."""

from datetime import datetime

from pydantic import Field

from geoops_api.domain.models import GeoPoint
from geoops_api.maps.models import RouteWaypoint
from geoops_api.schemas.catalog import ApiModel


class GeocodeRequest(ApiModel):
    address: str = Field(min_length=3, max_length=300)


class RouteRequest(ApiModel):
    origin: GeoPoint
    destination: GeoPoint
    departure_time: datetime | None = None


class RouteMatrixRequest(ApiModel):
    origins: list[RouteWaypoint] = Field(min_length=1, max_length=25)
    destinations: list[RouteWaypoint] = Field(min_length=1, max_length=25)
    departure_time: datetime | None = None
