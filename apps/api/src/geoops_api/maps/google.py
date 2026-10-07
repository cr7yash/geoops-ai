"""Google Maps Platform adapter for Geocoding v4 and Routes v2."""

import json
from datetime import datetime
from typing import Any, cast
from urllib.parse import quote

import httpx

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


class GoogleMapsProvider:
    """Call Google Maps web services through a narrow typed boundary."""

    name = "google"
    _GEOCODING_BASE_URL = "https://geocode.googleapis.com/v4/geocode/address"
    _ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
    _MATRIX_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"

    def __init__(
        self,
        api_key: str,
        *,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Google Maps API key must not be empty")
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def geocode(self, address: str) -> GeocodeResult:
        url = f"{self._GEOCODING_BASE_URL}/{quote(address, safe='')}"
        payload = await self._get_json(
            url,
            field_mask=(
                "results.location,results.formattedAddress,results.placeId,results.granularity"
            ),
        )
        results = cast(list[dict[str, Any]], payload.get("results", []))
        if not results:
            raise GeocodeNotFoundError(f"Google returned no geocode for {address!r}")
        first = results[0]
        location = cast(dict[str, float], first["location"])
        return GeocodeResult(
            provider=self.name,
            formatted_address=str(first.get("formattedAddress", address)),
            location=GeoPoint(
                latitude=float(location["latitude"]),
                longitude=float(location["longitude"]),
            ),
            place_id=(str(first["placeId"]) if first.get("placeId") else None),
            precision=(str(first["granularity"]) if first.get("granularity") else None),
        )

    async def compute_route(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        *,
        departure_time: datetime,
    ) -> RouteResult:
        payload = await self._post_json(
            self._ROUTES_URL,
            body={
                "origin": self._waypoint_payload(origin),
                "destination": self._waypoint_payload(destination),
                "travelMode": "DRIVE",
                "routingPreference": "TRAFFIC_AWARE",
                "departureTime": departure_time.isoformat().replace("+00:00", "Z"),
            },
            field_mask="routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline",
        )
        routes = cast(list[dict[str, Any]], payload.get("routes", []))
        if not routes:
            return RouteResult(
                provider=self.name,
                status=RouteElementStatus.NO_ROUTE,
                origin=origin,
                destination=destination,
                departure_time=departure_time,
                is_estimate=False,
                error_message="Google returned no route",
            )
        route = routes[0]
        polyline = cast(dict[str, Any], route.get("polyline", {}))
        return RouteResult(
            provider=self.name,
            status=RouteElementStatus.OK,
            origin=origin,
            destination=destination,
            distance_km=round(float(route["distanceMeters"]) / 1000, 1),
            duration_minutes=round(self._duration_seconds(str(route["duration"])) / 60, 1),
            departure_time=departure_time,
            is_estimate=False,
            encoded_polyline=(
                str(polyline["encodedPolyline"]) if polyline.get("encodedPolyline") else None
            ),
        )

    async def compute_route_matrix(
        self,
        origins: list[RouteWaypoint],
        destinations: list[RouteWaypoint],
        *,
        departure_time: datetime,
    ) -> RouteMatrixResult:
        if not origins or not destinations:
            return RouteMatrixResult(
                provider=self.name,
                departure_time=departure_time,
                is_estimate=False,
                elements=[],
            )
        records = await self._post_stream(
            self._MATRIX_URL,
            body={
                "origins": [
                    {"waypoint": self._waypoint_payload(item.location)} for item in origins
                ],
                "destinations": [
                    {"waypoint": self._waypoint_payload(item.location)} for item in destinations
                ],
                "travelMode": "DRIVE",
                "routingPreference": "TRAFFIC_AWARE",
                "departureTime": departure_time.isoformat().replace("+00:00", "Z"),
            },
            field_mask=("originIndex,destinationIndex,status,condition,distanceMeters,duration"),
        )
        elements: list[RouteMatrixElement] = []
        for record in records:
            origin_index = int(record["originIndex"])
            destination_index = int(record["destinationIndex"])
            status_payload = cast(dict[str, Any], record.get("status", {}))
            status_code = int(status_payload.get("code", 0))
            condition = str(record.get("condition", ""))
            if status_code != 0:
                element_status = RouteElementStatus.PROVIDER_ERROR
            elif condition == "ROUTE_EXISTS":
                element_status = RouteElementStatus.OK
            else:
                element_status = RouteElementStatus.NO_ROUTE
            elements.append(
                RouteMatrixElement(
                    origin_id=origins[origin_index].waypoint_id,
                    destination_id=destinations[destination_index].waypoint_id,
                    status=element_status,
                    distance_km=(
                        round(float(record["distanceMeters"]) / 1000, 1)
                        if record.get("distanceMeters") is not None
                        else None
                    ),
                    duration_minutes=(
                        round(
                            self._duration_seconds(str(record["duration"])) / 60,
                            1,
                        )
                        if record.get("duration")
                        else None
                    ),
                    error_message=(
                        str(status_payload.get("message", "Route was not found"))
                        if element_status != RouteElementStatus.OK
                        else None
                    ),
                )
            )
        return RouteMatrixResult(
            provider=self.name,
            departure_time=departure_time,
            is_estimate=False,
            elements=elements,
        )

    async def _get_json(self, url: str, *, field_mask: str) -> dict[str, Any]:
        async with self._client() as client:
            try:
                response = await client.get(
                    url,
                    headers=self._headers(field_mask),
                )
                response.raise_for_status()
            except httpx.HTTPError as error:
                raise MapsProviderError(f"Google Maps request failed: {error}") from error
        return cast(dict[str, Any], response.json())

    async def _post_json(
        self, url: str, *, body: dict[str, Any], field_mask: str
    ) -> dict[str, Any]:
        async with self._client() as client:
            try:
                response = await client.post(
                    url,
                    headers=self._headers(field_mask),
                    json=body,
                )
                response.raise_for_status()
            except httpx.HTTPError as error:
                raise MapsProviderError(f"Google Maps request failed: {error}") from error
        return cast(dict[str, Any], response.json())

    async def _post_stream(
        self, url: str, *, body: dict[str, Any], field_mask: str
    ) -> list[dict[str, Any]]:
        async with self._client() as client:
            try:
                response = await client.post(
                    url,
                    headers=self._headers(field_mask),
                    json=body,
                )
                response.raise_for_status()
            except httpx.HTTPError as error:
                raise MapsProviderError(f"Google Maps request failed: {error}") from error
        try:
            payload = response.json()
        except json.JSONDecodeError:
            payload = [json.loads(line) for line in response.text.splitlines() if line]
        if isinstance(payload, list):
            return cast(list[dict[str, Any]], payload)
        raise MapsProviderError("Google route matrix returned an unexpected payload")

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self._timeout_seconds,
            transport=self._transport,
        )

    def _headers(self, field_mask: str) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": field_mask,
        }

    @staticmethod
    def _waypoint_payload(point: GeoPoint) -> dict[str, Any]:
        return {
            "location": {
                "latLng": {
                    "latitude": point.latitude,
                    "longitude": point.longitude,
                }
            }
        }

    @staticmethod
    def _duration_seconds(value: str) -> float:
        if not value.endswith("s"):
            raise MapsProviderError(f"Unexpected Google duration value: {value}")
        return float(value[:-1])
