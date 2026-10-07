"""Provider-neutral geocoding and routing values."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from geoops_api.domain.models import GeoPoint


class MapsModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RouteElementStatus(StrEnum):
    OK = "ok"
    NO_ROUTE = "no_route"
    PROVIDER_ERROR = "provider_error"


class GeocodeResult(MapsModel):
    provider: str
    formatted_address: str
    location: GeoPoint
    place_id: str | None = None
    precision: str | None = None


class RouteWaypoint(MapsModel):
    waypoint_id: str
    location: GeoPoint


class RouteResult(MapsModel):
    provider: str
    status: RouteElementStatus
    origin: GeoPoint
    destination: GeoPoint
    distance_km: float | None = Field(default=None, ge=0)
    duration_minutes: float | None = Field(default=None, ge=0)
    departure_time: datetime
    is_estimate: bool
    encoded_polyline: str | None = None
    error_message: str | None = None


class RouteMatrixElement(MapsModel):
    origin_id: str
    destination_id: str
    status: RouteElementStatus
    distance_km: float | None = Field(default=None, ge=0)
    duration_minutes: float | None = Field(default=None, ge=0)
    error_message: str | None = None


class RouteMatrixResult(MapsModel):
    provider: str
    departure_time: datetime
    is_estimate: bool
    elements: list[RouteMatrixElement]


class MapsProviderError(RuntimeError):
    """Raised when a configured maps provider cannot complete a request."""


class GeocodeNotFoundError(MapsProviderError):
    """Raised when an address has no geocoding result."""
