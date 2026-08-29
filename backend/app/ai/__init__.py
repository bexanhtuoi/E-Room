from langchain.agents import create_agent as create_langchain_agent
from langchain_openai import ChatOpenAI

from app.ai.prompt import get_main_prompt
from app.ai.tools import retrieval_documents, web_search
from app.config import settings


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        # llama.cpp bo qua auth nhung client OpenA I khong chap nhan key rong
        api_key=settings.llm_api_key or "not-needed",
        timeout=settings.ai_timeout_seconds,
    )


def get_agent():
    return create_langchain_agent(
        model=get_llm(),
        tools=[retrieval_documents, web_search],
        system_prompt=get_main_prompt(),
    )
