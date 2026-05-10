from __future__ import annotations

import re
from typing import Any

from langchain_core.documents import Document
from langchain_core.runnables.config import run_in_executor

from app.log import get_logger
from app.rag.vector_store import init_vector_store

logger = get_logger(__name__)


def _keyword_score(text: str, query: str) -> float:
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
) -> list[dict[str, Any]]:
    vs = init_vector_store()
    filter_dict = {"tag": tag} if tag is not None else None
    try:
        docs: list[Document] = await run_in_executor(
            None, vs.similarity_search, query, k, filter=filter_dict
        )
    except Exception as e:
        logger.warning("retrieval_tidb_failed", extra={"error": str(e)})
        return []
    results = []
    for doc in docs:
        text = doc.page_content
        kw = _keyword_score(text, query)
        results.append({
            "text": text,
            "metadata": doc.metadata,
            "combined_score": kw,
        })
    results.sort(key=lambda x: x["combined_score"], reverse=True)
    seen: set[str] = set()
    deduped = []
    for item in results:
        text_key = item["text"][:100]
        if text_key not in seen:
            seen.add(text_key)
            deduped.append(item)
    return deduped[:k]


class RetrievalService:
    def __init__(self) -> None:
        self._vs = init_vector_store()

    async def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        try:
            docs: list[Document] = await run_in_executor(
                None, self._vs.similarity_search, query, top_k
            )
        except Exception as e:
            logger.warning("retrieval_failed", extra={"error": str(e)})
            return []
        results = []
        for doc in docs:
            text = doc.page_content
            kw = _keyword_score(text, query)
            results.append({
                "text": text,
                "metadata": doc.metadata,
                "combined_score": kw,
            })
        results.sort(key=lambda x: x["combined_score"], reverse=True)
        return results[:top_k]
