from __future__ import annotations

from typing import Any

import httpx
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.base import call_llm_text
from app.agent.prompt import EXPERT_SYSTEM_TEMPLATE
from app.config import settings
from app.log import get_logger

logger = get_logger(__name__)


def _extract_sources(docs: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    sources: list[str] = []
    for d in docs:
        metadata = d.get("metadata") or {}
        source = metadata.get("source") or metadata.get("filename") or metadata.get("title")
        if source and source not in seen:
            seen.add(source)
            sources.append(source)
    return sources


async def _web_search(query: str, tag: str | None = None) -> tuple[str, list[str]]:
    if not settings.brave_search_api_key:
        return "", []

    search_query = f"{query} {tag or ''}".strip()

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": settings.brave_search_api_key,
                },
                params={"q": search_query, "count": 3},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        sources = []
        for item in data.get("web", {}).get("results", [])[:3]:
            title = item.get("title", "")
            snippet = item.get("description", "") or item.get("snippet", "")
            url = item.get("url", "")
            results.append(f"{title}: {snippet}"[:300])
            if url:
                sources.append(url)

        return "\n\n".join(results), sources
    except Exception as e:
        logger.warning("Tra cứu web thất bại", extra={"query": query[:50], "error": str(e)})
        return "", []


async def answer_expert(question: str, room_id: str, tags: list[str] | None = None) -> dict[str, Any]:
    logger.info("Bắt đầu trả lời chuyên gia", extra={"room_id": room_id, "question": question[:80]})

    tag_str = ", ".join(tags) if tags else None

    try:
        from app.rag.retrieval import retrieve_relevant_documents

        docs = await retrieve_relevant_documents(question, k=5)
    except Exception as e:
        logger.warning("Truy xuất RAG thất bại", extra={"room_id": room_id, "error": str(e)})
        docs = []

    rag_context = "\n\n".join([d["text"][:500] for d in docs]) if docs else ""
    sources = _extract_sources(docs)

    web_context, web_sources = await _web_search(question, tag_str)
    sources.extend(web_sources)

    if rag_context:
        combined = f"Knowledge base:\n{rag_context}"
        if web_context:
            combined += f"\n\nWeb search results:\n{web_context}"
    elif web_context:
        combined = f"Web search results:\n{web_context}"
    else:
        combined = "No relevant documents or web results found."

    system_prompt = EXPERT_SYSTEM_TEMPLATE
    user_prompt = (
        f"Question: {question}\n\nContext:\n{combined}\n\n"
        "Provide a helpful answer. If from the web, mention source URLs."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    try:
        answer = await call_llm_text(messages, temperature=0.5)
        logger.info("Trả lời chuyên gia hoàn tất", extra={"room_id": room_id, "answer_len": len(answer)})
        return {"answer": answer, "sources": list(dict.fromkeys(sources))}
    except Exception as e:
        logger.error("Trả lời chuyên gia thất bại", exc_info=True, extra={"room_id": room_id, "error": str(e)})
        return {"answer": f"Sorry, I couldn't process your question: {e}", "sources": []}
