"""Private Cloud Run push receiver. Cloud Run IAM validates Pub/Sub OIDC tokens."""

import base64
import binascii

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field, ValidationError

from geoops_api.config import get_settings
from geoops_api.container import build_container
from geoops_api.workflow import DispatchEvent

app = FastAPI(title="GeoOps dispatch worker")
container = build_container(get_settings())


class PubSubMessage(BaseModel):
    data: str = Field(max_length=100_000)


class PushEnvelope(BaseModel):
    message: PubSubMessage


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "geoops-dispatch-worker"}


@app.post("/events", status_code=204)
async def consume(payload: PushEnvelope) -> Response:
    try:
        event = DispatchEvent.model_validate_json(
            base64.b64decode(payload.message.data, validate=True)
        )
    except (binascii.Error, ValidationError) as exc:
        raise HTTPException(400, "Invalid event envelope") from exc
    await container.dispatch_worker.consume(event)
    return Response(status_code=204)


@app.post("/relay")
async def relay() -> dict[str, int]:
    return {
        "published": await container.outbox_relay.run_once(),
        "archived": await container.analytics_relay.run_once(),
    }
