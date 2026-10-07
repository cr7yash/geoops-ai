"""Embedding provider implementations for key-free local retrieval."""

import hashlib
import re
from collections import Counter
from itertools import pairwise
from math import log, sqrt


class DeterministicEmbeddingProvider:
    """Produce stable normalized hashing-vector embeddings without network calls."""

    name = "deterministic-hashing-v1"
    _TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

    def __init__(self, dimensions: int = 64) -> None:
        if dimensions < 16:
            raise ValueError("Embedding dimensions must be at least 16")
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        tokens = self._TOKEN_PATTERN.findall(text.casefold())
        features = tokens + [f"{left}_{right}" for left, right in pairwise(tokens)]
        counts = Counter(features)
        vector = [0.0] * self._dimensions
        for token, count in sorted(counts.items()):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self._dimensions
            vector[bucket] += 1 + log(count)
        magnitude = sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return vector
        return [round(value / magnitude, 10) for value in vector]
