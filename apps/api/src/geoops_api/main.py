"""FastAPI application factory and ASGI entrypoint."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from geoops_api.config import Settings, get_settings
from geoops_api.container import ApplicationContainer, build_container
from geoops_api.logging import configure_logging
from geoops_api.middleware import RequestTelemetryMiddleware
from geoops_api.routers.agent import router as agent_router
from geoops_api.routers.approvals import router as approvals_router
from geoops_api.routers.dispatch import router as dispatch_router
from geoops_api.routers.health import router as health_router
from geoops_api.routers.knowledge import router as knowledge_router
from geoops_api.routers.maps import router as maps_router
from geoops_api.routers.technicians import router as technicians_router
from geoops_api.routers.tickets import router as tickets_router


def create_app(
    settings: Settings | None = None,
    container: ApplicationContainer | None = None,
) -> FastAPI:
    """Construct the API with explicit, testable dependencies."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)
    resolved_container = container or build_container(resolved_settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        task = (
            asyncio.create_task(
                resolved_container.outbox_relay.run(resolved_settings.worker_poll_seconds)
            )
            if resolved_settings.worker_enabled
            else None
        )
        yield
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        await resolved_container.event_bus.close()
        await resolved_container.approval_repository.store.close()

    application = FastAPI(
        title="GeoOps AI API",
        summary="Operations gateway for the GeoOps AI platform.",
        version=resolved_settings.version,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.container = resolved_container

    application.add_middleware(RequestTelemetryMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health_router)
    application.include_router(tickets_router)
    application.include_router(technicians_router)
    application.include_router(dispatch_router)
    application.include_router(maps_router)
    application.include_router(knowledge_router)
    application.include_router(agent_router)
    application.include_router(approvals_router)
    return application


app = create_app()
