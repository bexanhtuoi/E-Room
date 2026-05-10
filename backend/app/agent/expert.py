from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import requests

from app.agent.prompt import EXPERT_SYSTEM_TEMPLATE
from app.log import get_logger

logger = get_logger(__name__)


class AgentExpert:
    """AI expert that answers questions using RAG context and web search."""

    def __init__(self) -> None:
        self._llm_base = self._get_llm_base()
        self._llm_model = self._get_llm_model()
        self._api_key = self._get_api_key()

    def _get_llm_base(self) -> str:
        try:
            from app.config import settings
            return getattr(settings, "llm_base_url", os.getenv("LLM_BASE_URL", "http://localhost:20128/v1"))
        except ImportError:
            return os.getenv("LLM_BASE_URL", "http://localhost:20128/v1")

    def _get_llm_model(self) -> str:
        try:
            from app.config import settings
            return getattr(settings, "llm_model", os.getenv("LLM_MODEL", "ds2api/deepseek-v4-flash-nothinking"))
        except ImportError:
            return os.getenv("LLM_MODEL", "ds2api/deepseek-v4-flash-nothinking")

    def _get_api_key(self) -> str:
        try:
            from app.config import settings
            return getattr(settings, "llm_api_key", os.getenv("LLM_API_KEY", ""))
        except ImportError:
            return os.getenv("LLM_API_KEY", "")

    async def _retrieve_rag_docs(self, query: str, room_id: str) -> list[dict[str, Any]]:
        """Retrieve relevant documents from RAG vector store. Returns full doc list."""
        try:
            from app.rag.retrieval import retrieve_relevant_documents
            docs = await retrieve_relevant_documents(query, k=5)
            return docs if docs else []
        except Exception as e:
            logger.warning("rag_retrieval_failed", extra={"room_id": room_id, "error": str(e)})
            return []

    async def _generate_answer(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self._llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.5,
        }

        def _sync_post():
            resp = requests.post(
                f"{self._llm_base}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _sync_post)

    def _extract_sources(self, docs: list[dict[str, Any]]) -> list[str]:
        """Extract unique source identifiers from retrieved documents."""
        seen: set[str] = set()
        sources: list[str] = []
        for d in docs:
            metadata = d.get("metadata") or {}
            source = metadata.get("source") or metadata.get("filename") or metadata.get("title")
            if source and source not in seen:
                seen.add(source)
                sources.append(source)
        return sources

    async def answer(self, question: str, room_id: str) -> dict[str, Any]:
        """Answer a question with RAG context and citations."""
        logger.info("expert_start", extra={"room_id": room_id, "question": question[:80]})

        docs = await self._retrieve_rag_docs(question, room_id)
        rag_context = "\n\n".join([d["text"][:500] for d in docs]) if docs else ""
        sources = self._extract_sources(docs)

        system_prompt = EXPERT_SYSTEM_TEMPLATE
        user_prompt = (
            f"Question: {question}\n\n"
            f"Relevant context from knowledge base:\n"
            f"{rag_context or 'No relevant documents found.'}\n\n"
            f"Provide a helpful answer with citations where applicable."
        )

        try:
            answer = await self._generate_answer(system_prompt, user_prompt)
            logger.info("expert_done", extra={"room_id": room_id, "answer_len": len(answer)})
            return {"answer": answer, "sources": sources}
        except Exception as e:
            logger.error("expert_failed", exc_info=True, extra={"room_id": room_id, "error": str(e)})
            return {"answer": f"Sorry, I couldn't process your question: {e}", "sources": []}
