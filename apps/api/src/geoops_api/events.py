"""Event transports. The outbox remains authoritative until delivery succeeds."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Protocol

import google.cloud.pubsub_v1 as pubsub_v1  # type: ignore[import-untyped]

from geoops_api.workflow import DispatchEvent

type Consumer = Callable[[DispatchEvent], Awaitable[None]]


class EventBus(Protocol):
    async def publish(self, event: DispatchEvent) -> None: ...
    async def close(self) -> None: ...


class InMemoryEventBus:
    def __init__(self) -> None:
        self._consumers: list[Consumer] = []

    def subscribe(self, consumer: Consumer) -> None:
        self._consumers.append(consumer)

    async def publish(self, event: DispatchEvent) -> None:
        for consumer in self._consumers:
            await consumer(event)

    async def close(self) -> None:
        return None


class GooglePubSubEventBus:
    def __init__(self, project: str, topic: str) -> None:
        self._client = pubsub_v1.PublisherClient()
        self._topic = self._client.topic_path(project, topic)

    async def publish(self, event: DispatchEvent) -> None:
        future = self._client.publish(
            self._topic, event.model_dump_json().encode(), event_id=event.event_id
        )
        await asyncio.to_thread(future.result, timeout=30)

    async def close(self) -> None:
        self._client.stop()
