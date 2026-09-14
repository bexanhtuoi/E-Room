from typing import Dict, Optional

import langchain_openai.chat_models.base as lc_base
from langchain.agents import create_agent as create_langchain_agent
from langchain_openai import ChatOpenAI

from app.ai.prompt import get_main_prompt
from app.ai.tools import retrieval_documents, web_search
from app.config import settings

_orig_convert = lc_base._convert_delta_to_message_chunk


def keep_reasoning_content(_dict, default_class):
    msg = _orig_convert(_dict, default_class)
    reasoning = _dict.get("reasoning_content") or _dict.get("reasoning")
    if reasoning is not None and hasattr(msg, "additional_kwargs"):
        msg.additional_kwargs = {**(msg.additional_kwargs or {}), "reasoning_content": reasoning}
    return msg


lc_base._convert_delta_to_message_chunk = keep_reasoning_content


def is_openrouter(base_url: str) -> bool:
    return "openrouter" in (base_url or "").lower()


def reasoning_body(base_url: str) -> Dict[str, object]:
    if is_openrouter(base_url):
        return {"reasoning": {"effort": "low"}}

    return {
        "reasoning_effort": "low",
        "reasoning_format": "parsed",
    }


def get_llm(timeout: Optional[int] = None) -> ChatOpenAI:
    base_url = settings.llm_base_url

    return ChatOpenAI(
        base_url=base_url,
        model=settings.llm_model,
        api_key=settings.llm_api_key or "not-needed",
        timeout=timeout if timeout is not None else settings.llm_call_timeout_seconds,
        extra_body=reasoning_body(base_url),
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
