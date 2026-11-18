"""Container entrypoint for configured document ingestion."""

import asyncio

from geoops_api.config import Settings
from geoops_api.container import build_container


async def main() -> None:
    container = build_container(Settings())
    try:
        report = await container.knowledge_service.ingest()
        print(report.model_dump_json())
    finally:
        await container.event_bus.close()
        await container.approval_repository.store.close()


if __name__ == "__main__":
    asyncio.run(main())
