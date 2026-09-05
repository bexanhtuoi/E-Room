import langchain_openai.chat_models.base as lc_base
from langchain.agents import create_agent as create_langchain_agent
from langchain_openai import ChatOpenAI

from app.ai.prompt import get_main_prompt
from app.ai.tools import retrieval_documents, web_search
from app.config import settings

_orig_convert = lc_base._convert_delta_to_message_chunk


def keep_reasoning_content(_dict, default_class):
    # langchain-openai chu dong loai bo reasoning_content khoi SSE delta
    # (ghi ro trong source cua ho) — giu lai vao additional_kwargs de
    # stream thinking cua model. Da verify: server co tra, langchain lam rot.
    msg = _orig_convert(_dict, default_class)
    reasoning = _dict.get("reasoning_content") or _dict.get("reasoning")
    if reasoning is not None and hasattr(msg, "additional_kwargs"):
        msg.additional_kwargs = {**(msg.additional_kwargs or {}), "reasoning_content": reasoning}
    return msg


lc_base._convert_delta_to_message_chunk = keep_reasoning_content


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
