# GeoOps API

FastAPI gateway for GeoOps AI. It exposes health, read-only operational catalogs, route-aware dispatch, provider-neutral maps endpoints, cited knowledge retrieval, and typed agent orchestration. The default maps, embedding, and agent implementations need no credentials. The agent can also run through Google ADK with the Gemini Developer API or Vertex AI; see the root configuration reference for server-only credentials.

From the repository root, start it with `make api` and open the generated API documentation at <http://localhost:8000/docs>.
