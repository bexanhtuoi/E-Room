import langchain_openai.chat_models.base as lc_base

from app.ai.llm.client import get_agent, get_llm, is_openrouter, reasoning_body

_orig_convert = lc_base._convert_delta_to_message_chunk


def keep_reasoning_content(_dict, default_class):
    msg = _orig_convert(_dict, default_class)
    reasoning = _dict.get("reasoning_content") or _dict.get("reasoning")
    if reasoning is not None and hasattr(msg, "additional_kwargs"):
        msg.additional_kwargs = {**(msg.additional_kwargs or {}), "reasoning_content": reasoning}
    return msg


lc_base._convert_delta_to_message_chunk = keep_reasoning_content

__all__ = [
    "get_agent",
    "get_llm",
    "is_openrouter",
    "keep_reasoning_content",
    "reasoning_body",
]
