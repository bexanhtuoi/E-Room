from __future__ import annotations

from app.agent.corrector import AgentCorrector
from app.agent.expert import AgentExpert
from app.agent.heartbeat import AgentHeartbeat

__all__ = ["AgentCorrector", "AgentExpert", "AgentHeartbeat", "get_llm", "get_knowledge_agent"]

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from app.config import settings


def get_llm(model: str | None = None, temperature: float = 0) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        model=model or settings.llm_model,
        api_key=settings.llm_api_key,
        temperature=temperature,
    )


async def get_knowledge_agent(model: str | None = None):
    llm = get_llm(model=model)
    return create_agent(
        llm,
        system_prompt=(
            "You are a helpful knowledge assistant. "
            "Answer the user's question accurately and concisely."
        ),
    )
