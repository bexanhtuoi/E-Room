from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any

from langchain_nomic import NomicEmbeddings

from app.config import settings
from app.log import get_logger

logger = get_logger(__name__)

_DEFAULT_EMBEDDING_DIM = 768
_BATCH_SIZE = 20


def _cache_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:32]


def get_embedding_model(model_name: str = "nomic-embed-text-v1.5") -> NomicEmbeddings:
    return NomicEmbeddings(
        model=model_name,
        nomic_api_key=settings.nomic_api_key,
        dimensionality=768,
        inference_mode="remote",
    )


class EmbeddingService:

    def __init__(self, model_name: str = "nomic-embed-text-v1.5") -> None:
        self._model_name = model_name
        self._cache: dict[str, list[float]] = {}
        self._dim = _DEFAULT_EMBEDDING_DIM
        self._nomic_emb: NomicEmbeddings | None = None

    def _get_embeddings(self) -> NomicEmbeddings:
        if self._nomic_emb is None:
            self._nomic_emb = get_embedding_model(self._model_name)
        return self._nomic_emb

    def _load_from_redis(self, key: str) -> list[float] | None:
        try:
            from app.infrastructure.redis_client import RedisCRUD

            redis = RedisCRUD()
            cached = redis.get(f"emb:{key}")
            if cached:
                return json.loads(cached)
        except Exception:
            pass
        return None

    def _save_to_redis(self, key: str, vector: list[float]) -> None:
        try:
            from app.infrastructure.redis_client import RedisCRUD

            redis = RedisCRUD()
            redis.set(f"emb:{key}", json.dumps(vector), ttl=86400)
        except Exception:
            pass

    def _zero_vector(self) -> list[float]:
        return [0.0] * self._dim

    async def embed_query(self, text: str) -> list[float]:
        if not text or not text.strip():
            return self._zero_vector()

        key = _cache_key(text)

        if key in self._cache:
            return self._cache[key]

        redis_val = self._load_from_redis(key)
        if redis_val is not None:
            self._cache[key] = redis_val
            return redis_val

        try:
            emb = self._get_embeddings()
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, emb.embed_query, text)
        except Exception as e:
            logger.warning("embed_failed", extra={"error": str(e)})
            result = self._zero_vector()

        self._cache[key] = result
        self._save_to_redis(key, result)
        return result

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        results: list[list[float] | None] = [None] * len(texts)
        uncached: list[tuple[int, str]] = []

        for idx, text in enumerate(texts):
            if not text or not text.strip():
                results[idx] = self._zero_vector()
                continue

            key = _cache_key(text)

            if key in self._cache:
                results[idx] = self._cache[key]
                continue

            redis_val = self._load_from_redis(key)
            if redis_val is not None:
                self._cache[key] = redis_val
                results[idx] = redis_val
                continue

            uncached.append((idx, text))

        if not uncached:
            return [r for r in results if r is not None]

        emb = self._get_embeddings()
        loop = asyncio.get_running_loop()

        for batch_start in range(0, len(uncached), _BATCH_SIZE):
            batch = uncached[batch_start : batch_start + _BATCH_SIZE]
            batch_texts = [t for _, t in batch]
            batch_indices = [i for i, _ in batch]

            try:
                vectors = await loop.run_in_executor(
                    None, emb.embed_documents, batch_texts
                )
            except Exception as e:
                logger.warning("embed_batch_failed", extra={"error": str(e)})
                vectors = [self._zero_vector() for _ in batch_texts]

            for i, vec in zip(batch_indices, vectors):
                results[i] = vec
                key = _cache_key(texts[i])
                self._cache[key] = vec
                self._save_to_redis(key, vec)

        final: list[list[float]] = []
        for r in results:
            final.append(r if r is not None else self._zero_vector())
        return final

    async def embed_text(self, text: str) -> list[float]:
        return await self.embed_query(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return await self.embed_texts(texts)
