from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any

import httpx

from app.config import settings
from app.log import get_logger

logger = get_logger(__name__)

_DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
_DEFAULT_EMBEDDING_DIM = 1536
_BATCH_SIZE = 20

_local_embedder: Any = None


def _get_local_embedder() -> Any:
    """Lazy-load FlagEmbedding model for local fallback."""
    global _local_embedder
    if _local_embedder is not None:
        return _local_embedder
    try:
        from FlagEmbedding import FlagModel

        _local_embedder = FlagModel("BAAI/bge-small-en-v1.5", use_fp16=True)
        logger.info("local_embedder_loaded", extra={"model": "BAAI/bge-small-en-v1.5"})
    except ImportError:
        logger.warning("flagembedding_not_installed")
        _local_embedder = False
    except Exception as e:
        logger.warning("local_embedder_load_failed", extra={"error": str(e)})
        _local_embedder = False
    return _local_embedder


def _cache_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:32]


class EmbeddingService:
    """Text embedding via OpenAI-compatible API with optional local fallback.

    Caches results in-memory and optionally in Redis. Falls back to a
    local FlagEmbedding model when the API is unreachable.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str = _DEFAULT_EMBEDDING_MODEL,
    ) -> None:
        self._base_url = (base_url or settings.llm_base_url).rstrip("/")
        self._api_key = api_key or settings.llm_api_key
        self._model = model
        self._cache: dict[str, list[float]] = {}
        self._dim = _DEFAULT_EMBEDDING_DIM

    def _load_from_redis(self, key: str) -> list[float] | None:
        try:
            from app.infrastructure.redis import RedisCRUD

            redis = RedisCRUD()
            cached = redis.get(f"emb:{key}")
            if cached:
                return json.loads(cached)
        except Exception:
            pass
        return None

    def _save_to_redis(self, key: str, vector: list[float]) -> None:
        try:
            from app.infrastructure.redis import RedisCRUD

            redis = RedisCRUD()
            redis.set(f"emb:{key}", json.dumps(vector), ttl=86400)
        except Exception:
            pass

    def _embed_local(self, texts: list[str]) -> list[list[float]]:
        embedder = _get_local_embedder()
        if embedder and embedder is not False:
            try:
                vectors = embedder.encode(texts)
                return [v.tolist() for v in vectors]
            except Exception as e:
                logger.warning("local_embed_failed", extra={"error": str(e)})
        return []

    def _zero_vector(self) -> list[float]:
        return [0.0] * self._dim

    async def _call_api(self, texts: list[str]) -> list[list[float]]:
        """Call the OpenAI-compatible embeddings endpoint."""
        url = f"{self._base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self._model, "input": texts}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]

    async def embed_query(self, text: str) -> list[float]:
        """Generate an embedding vector for a single query string.

        Args:
            text: The query text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        if not text or not text.strip():
            return self._zero_vector()

        key = _cache_key(text)
        if key in self._cache:
            return self._cache[key]

        redis_val = self._load_from_redis(key)
        if redis_val is not None:
            self._cache[key] = redis_val
            return redis_val

        vector = await self._embed_with_fallback([text])
        result = vector[0] if vector else self._zero_vector()

        self._cache[key] = result
        self._save_to_redis(key, result)
        return result

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts with batching.

        Texts are processed in batches of up to 20 for API efficiency.
        Cached embeddings are reused, and only uncached texts are sent.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors in the same order as the input.
        """
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

        for batch_start in range(0, len(uncached), _BATCH_SIZE):
            batch = uncached[batch_start : batch_start + _BATCH_SIZE]
            batch_texts = [t for _, t in batch]
            batch_indices = [i for i, _ in batch]

            vectors = await self._embed_with_fallback(batch_texts)

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
        """Generate embedding for a single text (alias for embed_query).

        Args:
            text: The text to embed.

        Returns:
            Embedding vector as a list of floats.
        """
        return await self.embed_query(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts (alias for embed_texts).

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors.
        """
        return await self.embed_texts(texts)

    async def _embed_with_fallback(self, texts: list[str]) -> list[list[float]]:
        """Try API first, then local model, then zero vectors."""
        try:
            return await self._call_api(texts)
        except Exception as e:
            logger.warning("embed_api_failed", extra={"error": str(e)})

        local_result = self._embed_local(texts)
        if local_result:
            self._dim = len(local_result[0])
            return local_result

        logger.warning("embed_all_failed_zero_vectors")
        return [self._zero_vector() for _ in texts]


# ---------------------------------------------------------------------------
# Nomic embedding service (like flowassist)
# ---------------------------------------------------------------------------

_NOMIC_DIM = 768  # nomic-embed-text-v1.5 produces 768-dim vectors


class NomicEmbeddingService:
    """Text embedding via Nomic AI (like flowassist).

    Uses langchain_nomic.NomicEmbeddings with nomic-embed-text-v1.5.
    Produces 768-dimensional embeddings.
    NOMIC_API_KEY from .env (same key as flowassist).
    """

    def __init__(self, api_key: str | None = None) -> None:
        import os
        self._api_key = api_key or os.getenv("NOMIC_API_KEY", "")
        self._dim = _NOMIC_DIM
        self._cache: dict[str, list[float]] = {}
        self._nomic_emb = None

    def _get_embeddings(self):
        if self._nomic_emb is None:
            from langchain_nomic import NomicEmbeddings
            self._nomic_emb = NomicEmbeddings(
                model="nomic-embed-text-v1.5",
                nomic_api_key=self._api_key,
            )
        return self._nomic_emb

    def _zero_vector(self) -> list[float]:
        return [0.0] * self._dim

    async def embed_query(self, text: str) -> list[float]:
        if not text or not text.strip():
            return self._zero_vector()
        key = _cache_key(text)
        if key in self._cache:
            return self._cache[key]
        import asyncio
        emb = self._get_embeddings()
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, emb.embed_query, text)
        self._cache[key] = result
        return result

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        import asyncio
        emb = self._get_embeddings()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, emb.embed_documents, texts)

    async def embed_text(self, text: str) -> list[float]:
        return await self.embed_query(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return await self.embed_texts(texts)


_embed_service: EmbeddingService | NomicEmbeddingService | None = None


def get_embedding_service() -> EmbeddingService | NomicEmbeddingService:
    """Get or create the singleton embedding service instance.

    Prefers Nomic embeddings when NOMIC_API_KEY is set (like flowassist).
    Falls back to OpenAI-compatible EmbeddingService.
    """
    global _embed_service
    if _embed_service is not None:
        return _embed_service

    import os
    nomic_key = os.getenv("NOMIC_API_KEY", "")
    if nomic_key:
        _embed_service = NomicEmbeddingService(api_key=nomic_key)
        logger.info("embedding_service_nomic")
        return _embed_service

    _embed_service = EmbeddingService()
    return _embed_service
