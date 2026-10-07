"""Command-line entrypoint for validating and indexing local knowledge documents."""

import asyncio
import json

from geoops_api.config import Settings
from geoops_api.container import build_container


async def run() -> None:
    settings = Settings()
    report = await build_container(settings).knowledge_service.ingest()
    print(json.dumps(report.model_dump(), indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(run())
