from __future__ import annotations

from langchain.agents import create_agent
from langchain.tools import tool

from app.agent.corrector import correct_text
from app.agent.expert import answer_expert
from app.agent.heartbeat import generate_heartbeat
from app.agent.llm import get_llm
from app.log import get_logger
from app.rag.retrieval import retrieve_relevant_documents

logger = get_logger(__name__)

__all__ = [
    "answer_expert",
    "correct_text",
    "generate_heartbeat",
    "get_knowledge_agent",
    "get_llm",
    "search_knowledge",
]


@tool
async def search_knowledge(query: str, tag: str | None = None) -> str:
    """Search the RAG knowledge base for documents relevant to the query.

    Args:
        query: The search query string.
        tag: Optional tag/category to filter documents by.

    Returns:
        Relevant document passages joined with separators.
    """
    results = await retrieve_relevant_documents(query, k=5, tag=tag)
    if not results:
        return "No relevant documents found in the knowledge base."

    passages = []
    for i, r in enumerate(results, 1):
        text = r.get("text", "").strip()
        source = r.get("metadata", {}).get("source", "unknown")
        if text:
            passages.append(f"[{i}] (source: {source})\n{text}")

    return "\n\n---\n\n".join(passages)


async def get_knowledge_agent(model: str | None = None):
    llm = get_llm(model=model)
    return create_agent(
        llm,
        tools=[search_knowledge],
        system_prompt=(
            "You are a knowledgeable English tutoring assistant. "
            "You have access to a RAG knowledge base with documents about various topics. "
            "Use the search_knowledge tool to find relevant information when answering questions. "
            "Always provide clear, educational answers suitable for English learners. "
            "If the knowledge base doesn't have relevant information, say so and offer general help."
        ),
    )
