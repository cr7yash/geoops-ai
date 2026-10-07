# Maps providers

GeoOps isolates geocoding and driving-route operations behind an asynchronous `MapsProvider` protocol. Dispatch and API handlers consume the protocol, so provider selection does not alter eligibility or scoring code.

## Local mock provider

`MAPS_PROVIDER=mock` is the default and requires no credentials or network access. It provides:

- seed-address geocoding with normalized address matching;
- deterministic road-distance estimates using Haversine distance and a fixed factor;
- deterministic duration estimates using a fixed average speed;
- ordered route-matrix elements that retain application waypoint IDs; and
- a committed failure destination for testing unavailable-route behavior.

Every mock route response has `is_estimate: true`. It is useful for development and repeatable tests, not navigation.

## Google Maps provider

Set these server-side values:

```dotenv
MAPS_PROVIDER=google
GOOGLE_MAPS_API_KEY=replace-with-a-restricted-key
MAPS_TIMEOUT_SECONDS=10
```

The application refuses to start in Google mode with a missing or blank key. The adapter calls the [Geocoding API v4 address endpoint](https://developers.google.com/maps/documentation/geocoding/geocoding), [Routes API `computeRoutes`](https://developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRoutes), and [Routes API `computeRouteMatrix`](https://developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRouteMatrix). Requests send an explicit field mask to limit response data.

Restrict the key to the enabled APIs and the server environment. Never place it in `NEXT_PUBLIC_*` configuration.

## HTTP endpoints

| Endpoint | Request |
| --- | --- |
| `POST /api/maps/geocode` | Address string |
| `POST /api/maps/routes` | Origin, destination, and optional departure time |
| `POST /api/maps/route-matrix` | One to 25 origins, one to 25 destinations, and optional departure time |

Provider outages are returned as HTTP 502 for direct maps calls. In dispatch evaluation, route failures exclude affected prequalified candidates with `route_unavailable` so the recommendation cannot be based on missing travel evidence.
