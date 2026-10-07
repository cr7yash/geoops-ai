# GeoOps API

FastAPI gateway for GeoOps AI. It exposes the service health contract, read-only operational catalogs, route-aware dispatch recommendations, and provider-neutral maps endpoints. The default mock maps provider needs no credentials; set `MAPS_PROVIDER=google` and a server-only `GOOGLE_MAPS_API_KEY` to use Google Maps.

From the repository root, start it with `make api` and open the generated API documentation at <http://localhost:8000/docs>.
