"""Google Maps adapter tests use HTTP fixtures and never call Google."""

import json
from datetime import UTC, datetime

import httpx
import pytest

from geoops_api.domain.models import GeoPoint
from geoops_api.maps.google import GoogleMapsProvider
from geoops_api.maps.models import MapsProviderError, RouteWaypoint


@pytest.mark.anyio
async def test_google_geocode_maps_v4_response_and_headers() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.raw_path.endswith(b"/1600%20Amphitheatre%20Parkway")
        assert request.headers["X-Goog-Api-Key"] == "test-key"
        assert "results.location" in request.headers["X-Goog-FieldMask"]
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "location": {"latitude": 37.422, "longitude": -122.084},
                        "formattedAddress": "1600 Amphitheatre Pkwy, Mountain View, CA",
                        "placeId": "place-1",
                        "granularity": "PREMISE",
                    }
                ]
            },
        )

    provider = GoogleMapsProvider("test-key", transport=httpx.MockTransport(handler))
    result = await provider.geocode("1600 Amphitheatre Parkway")

    assert result.provider == "google"
    assert result.place_id == "place-1"
    assert result.location.latitude == 37.422


@pytest.mark.anyio
async def test_google_route_maps_distance_duration_and_polyline() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["travelMode"] == "DRIVE"
        assert payload["routingPreference"] == "TRAFFIC_AWARE"
        assert request.headers["X-Goog-FieldMask"].startswith("routes.duration")
        return httpx.Response(
            200,
            json={
                "routes": [
                    {
                        "distanceMeters": 12345,
                        "duration": "901.5s",
                        "polyline": {"encodedPolyline": "encoded"},
                    }
                ]
            },
        )

    provider = GoogleMapsProvider("test-key", transport=httpx.MockTransport(handler))
    result = await provider.compute_route(
        GeoPoint(latitude=37.7749, longitude=-122.4194),
        GeoPoint(latitude=37.8044, longitude=-122.2712),
        departure_time=datetime(2026, 10, 6, 16, tzinfo=UTC),
    )

    assert result.status == "ok"
    assert result.distance_km == 12.3
    assert result.duration_minutes == 15.0
    assert result.encoded_polyline == "encoded"
    assert result.is_estimate is False


@pytest.mark.anyio
async def test_google_matrix_preserves_waypoint_identity_and_failures() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/distanceMatrix/v2:computeRouteMatrix")
        return httpx.Response(
            200,
            json=[
                {
                    "originIndex": 0,
                    "destinationIndex": 0,
                    "status": {},
                    "condition": "ROUTE_EXISTS",
                    "distanceMeters": 3000,
                    "duration": "600s",
                },
                {
                    "originIndex": 1,
                    "destinationIndex": 0,
                    "status": {"code": 5, "message": "No route"},
                    "condition": "ROUTE_NOT_FOUND",
                },
            ],
        )

    provider = GoogleMapsProvider("test-key", transport=httpx.MockTransport(handler))
    result = await provider.compute_route_matrix(
        [
            RouteWaypoint(
                waypoint_id="tech-1",
                location=GeoPoint(latitude=37.77, longitude=-122.42),
            ),
            RouteWaypoint(
                waypoint_id="tech-2",
                location=GeoPoint(latitude=37.78, longitude=-122.41),
            ),
        ],
        [
            RouteWaypoint(
                waypoint_id="site-1",
                location=GeoPoint(latitude=37.80, longitude=-122.27),
            )
        ],
        departure_time=datetime(2026, 10, 6, 16, tzinfo=UTC),
    )

    assert result.elements[0].origin_id == "tech-1"
    assert result.elements[0].duration_minutes == 10.0
    assert result.elements[1].origin_id == "tech-2"
    assert result.elements[1].status == "provider_error"
    assert result.elements[1].error_message == "No route"


@pytest.mark.anyio
async def test_google_http_error_is_provider_neutral() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, request=request)

    provider = GoogleMapsProvider("test-key", transport=httpx.MockTransport(handler))
    with pytest.raises(MapsProviderError, match="Google Maps request failed"):
        await provider.geocode("Unavailable address")
