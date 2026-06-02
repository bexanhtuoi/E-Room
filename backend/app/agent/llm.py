from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.config import settings


def get_llm(model: str | None = None, temperature: float = 0) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        model=model or settings.llm_model,
        api_key=settings.llm_api_key,
        temperature=temperature,
    )
