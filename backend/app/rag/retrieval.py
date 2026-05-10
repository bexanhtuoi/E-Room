from __future__ import annotations

import re
from typing import Any

from app.log import get_logger
from app.rag.embedding import EmbeddingService
from app.rag.vector_store import VectorStore

logger = get_logger(__name__)

_vector_store: VectorStore | None = None
_embed_service: EmbeddingService | None = None


def _get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def _get_embed_service() -> EmbeddingService:
    global _embed_service
    if _embed_service is None:
        _embed_service = EmbeddingService()
    return _embed_service


def _keyword_score(text: str, query: str) -> float:
    """Simple BM25-inspired keyword scoring."""
    if not query.strip():
        return 0.0
    query_terms = re.findall(r"\w+", query.lower())
    text_terms = re.findall(r"\w+", text.lower())
    if not query_terms:
        return 0.0
    score = 0.0
    for qt in query_terms:
        tf = text_terms.count(qt)
        if tf > 0:
            score += tf / (tf + 1.5) * (1.0 / len(query_terms))
    return min(score, 1.0)


async def retrieve_relevant_documents(
    query: str,
    k: int = 10,
    tag: str | None = None,
    vector_weight: float = 0.7,
) -> list[dict[str, Any]]:
    """Hybrid search combining vector similarity and keyword matching."""
    vs = _get_vector_store()
    embed = _get_embed_service()

    query_vec = await embed.embed_text(query)
    if all(v == 0.0 for v in query_vec):
        logger.warning("zero_vector_embedding", extra={"query": query[:80]})
        return await _keyword_only_search(query, k, tag)

    vector_results = vs.similarity_search(query_vec, top_k=k * 2, tag_id=tag)
    if not vector_results:
        return []

    scored: list[dict[str, Any]] = []
    for item in vector_results:
        text = item.get("text", "")
        vs_score = item.get("score", 0.0)
        kw_score = _keyword_score(text, query)
        combined = vector_weight * vs_score + (1 - vector_weight) * kw_score
        scored.append({**item, "vector_score": vs_score, "keyword_score": kw_score, "combined_score": combined})

    scored.sort(key=lambda x: x["combined_score"], reverse=True)

    seen_texts: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in scored:
        text_key = item.get("text", "")[:100]
        if text_key not in seen_texts:
            seen_texts.add(text_key)
            deduped.append(item)
    return deduped[:k]


async def _keyword_only_search(query: str, k: int, tag: str | None = None) -> list[dict[str, Any]]:
    """Fallback keyword search when embedding is unavailable."""
    vs = _get_vector_store()
    all_results = vs.similarity_search([0.0] * 1536, top_k=1000, tag_id=tag)
    scored: list[dict[str, Any]] = []
    for item in all_results:
        kw = _keyword_score(item.get("text", ""), query)
        if kw > 0:
            scored.append({**item, "combined_score": kw})
    scored.sort(key=lambda x: x["combined_score"], reverse=True)
    return scored[:k]


class RetrievalService:
    def __init__(self) -> None:
        self._vector_store = _get_vector_store()
        self.embedding = _get_embed_service()

    async def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        query_vec = await self.embedding.embed_text(query)
        if all(v == 0.0 for v in query_vec):
            logger.warning("zero_vector_embedding", extra={"query": query[:80]})
            return []

        vector_results = self._vector_store.similarity_search(query_vec, top_k=top_k * 2)
        if not vector_results:
            return []

        scored: list[dict[str, Any]] = []
        for item in vector_results:
            text = item.get("text", "")
            vs_score = item.get("score", 0.0)
            kw_score = _keyword_score(text, query)
            combined = 0.7 * vs_score + 0.3 * kw_score
            scored.append({**item, "vector_score": vs_score, "keyword_score": kw_score, "combined_score": combined})

        scored.sort(key=lambda x: x["combined_score"], reverse=True)

        seen_texts: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for item in scored:
            text_key = item.get("text", "")[:100]
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                deduped.append(item)
        return deduped[:top_k]
