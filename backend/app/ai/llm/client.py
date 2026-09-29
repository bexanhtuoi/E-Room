from typing import Dict, Optional

from langchain.agents import create_agent as create_langchain_agent
from langchain_openai import ChatOpenAI

from app.ai.llm.prompt import get_main_prompt
from app.ai.llm.tools import retrieval_documents, web_search
from app.config import settings


def is_openrouter(base_url: str) -> bool:
    return "openrouter" in (base_url or "").lower()


def reasoning_body(base_url: str, effort: str = "low") -> Dict[str, object]:
    if (effort or "").strip().lower() in ("exclude", "none", "off"):
        if is_openrouter(base_url):
            return {"reasoning": {"exclude": True}}
        return {}
    if is_openrouter(base_url):
        return {"reasoning": {"effort": "low"}}

    return {
        "reasoning_effort": "low",
        "reasoning_format": "parsed",
    }


def get_llm(timeout: Optional[int] = None, model: Optional[str] = None,
            temperature: Optional[float] = None, max_tokens: Optional[int] = None,
            reasoning: str = "low") -> ChatOpenAI:
    base_url = settings.llm_base_url

    return ChatOpenAI(
        base_url=base_url,
        model=(model or "").strip() or settings.llm_model,
        api_key=settings.llm_api_key or "not-needed",
        timeout=timeout if timeout is not None else settings.llm_call_timeout_seconds,
        extra_body=reasoning_body(base_url, reasoning),
        **({"temperature": temperature} if temperature is not None else {}),
        **({"max_tokens": max_tokens} if max_tokens is not None else {}),
    )


def get_agent(tools=None, prompt=None, model=None, system_extra: str = ""):
    model = model or get_llm()
    tools = tools if tools is not None else [retrieval_documents, web_search]
    system_prompt = prompt if prompt is not None else get_main_prompt()
    if system_extra.strip():
        system_prompt = f"{system_prompt}\n\n{system_extra.strip()}"

    return create_langchain_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
    )
