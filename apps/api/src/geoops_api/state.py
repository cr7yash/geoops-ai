"""Transactional operational documents, with SQLite and Firestore adapters."""

import asyncio
import json
import sqlite3
from collections.abc import Callable
from pathlib import Path
from threading import Lock
from typing import Any, Protocol

from google.cloud.firestore_v1 import AsyncClient, AsyncTransaction, async_transactional

type Document = dict[str, Any]
type Mutation = Callable[[dict[str, Document | None]], dict[str, Document]]


class DocumentStore(Protocol):
    async def get(self, key: str) -> Document | None: ...
    async def scan(self, collection: str) -> list[Document]: ...
    async def transact(self, keys: list[str], mutate: Mutation) -> None: ...
    async def close(self) -> None: ...


class SQLiteDocumentStore:
    """Serialize read-modify-write operations across connections and processes."""

    def __init__(self, path: str = ":memory:") -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, check_same_thread=False, timeout=10)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS documents (key TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )
        self._lock = Lock()

    async def get(self, key: str) -> Document | None:
        def read() -> Document | None:
            with self._lock:
                row = self._connection.execute(
                    "SELECT body FROM documents WHERE key = ?", (key,)
                ).fetchone()
                return json.loads(row[0]) if row else None

        return await asyncio.to_thread(read)

    async def scan(self, collection: str) -> list[Document]:
        def read() -> list[Document]:
            with self._lock:
                return [
                    json.loads(row[0])
                    for row in self._connection.execute(
                        "SELECT body FROM documents WHERE key LIKE ? ORDER BY key",
                        (collection + "/%",),
                    )
                ]

        return await asyncio.to_thread(read)

    async def transact(self, keys: list[str], mutate: Mutation) -> None:
        def execute() -> None:
            with self._lock:
                self._connection.execute("BEGIN IMMEDIATE")
                try:
                    documents: dict[str, Document | None] = {}
                    for key in keys:
                        row = self._connection.execute(
                            "SELECT body FROM documents WHERE key = ?", (key,)
                        ).fetchone()
                        documents[key] = json.loads(row[0]) if row else None
                    for key, body in mutate(documents).items():
                        self._connection.execute(
                            "INSERT INTO documents VALUES (?, ?) ON CONFLICT(key) "
                            "DO UPDATE SET body = excluded.body",
                            (key, json.dumps(body)),
                        )
                    self._connection.commit()
                except BaseException:
                    self._connection.rollback()
                    raise

        await asyncio.to_thread(execute)

    async def close(self) -> None:
        await asyncio.to_thread(self._connection.close)


class FirestoreDocumentStore:
    def __init__(self, project: str, namespace: str = "geoops") -> None:
        self._client = AsyncClient(project=project)
        self._root = self._client.collection("workspaces").document(namespace)

    async def get(self, key: str) -> Document | None:
        snapshot = await self._client.document(self._root.path + "/" + key).get()
        return snapshot.to_dict() if snapshot.exists else None

    async def scan(self, collection: str) -> list[Document]:
        return [
            snapshot.to_dict() or {}
            async for snapshot in self._root.collection(collection).stream()
        ]

    async def transact(self, keys: list[str], mutate: Mutation) -> None:
        @async_transactional
        async def execute(transaction: AsyncTransaction) -> None:
            documents: dict[str, Document | None] = {}
            for key in keys:
                snapshot = await self._client.document(self._root.path + "/" + key).get(
                    transaction=transaction
                )
                documents[key] = snapshot.to_dict() if snapshot.exists else None
            for key, body in mutate(documents).items():
                transaction.set(self._client.document(self._root.path + "/" + key), body)

        await execute(self._client.transaction())

    async def close(self) -> None:
        self._client.close()  # type: ignore[no-untyped-call]
