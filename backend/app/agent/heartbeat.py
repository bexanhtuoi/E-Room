from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import requests

from app.agent.prompt import HEARTBEAT_SYSTEM_TEMPLATE
from app.log import get_logger

logger = get_logger(__name__)


class AgentHeartbeat:
    """Generates conversation starter questions for practice rooms."""

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

    async def generate(
        self,
        room_id: str,
        topic: str,
        tags: list[str] | None = None,
        recent_messages: list[dict] | None = None,
        heartbeat_count: int = 1,
    ) -> dict[str, Any]:
        """Generate a conversation starter question for the room."""
        logger.info("heartbeat_start", extra={"room_id": room_id, "heartbeat_count": heartbeat_count})

        tag_str = ", ".join(tags) if tags else "general English"
        last_msgs = recent_messages[-5:] if recent_messages else []
        msg_summary = "\n".join([f"{m.get('user_name', 'User')}: {m.get('content', '')[:100]}" for m in last_msgs])

        style = ""
        if heartbeat_count == 1:
            style = "icebreaker, light, fun, easy to answer"
        elif heartbeat_count == 2:
            style = "deeper, thought-provoking, encourages personal reflection"
        else:
            style = "challenging, hypothetical, opinion-based, or speculative"

        system_prompt = HEARTBEAT_SYSTEM_TEMPLATE
        user_prompt = f"""Room topic: {topic or "English conversation"}
Interests: {tag_str}
Recent messages (last 5):
{msg_summary or "No recent messages."}
Heartbeat number: {heartbeat_count}
Desired style: {style}

Generate a JSON object with:
- "question": the question to ask
- "context": why this question fits
- "suggested_response": a sample answer"""

        payload = {
            "model": self._llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.8,
            "response_format": {"type": "json_object"},
        }

        try:
            result = await self._call_llm(payload)
            question = result.get("question", f"What do you think about {tag_str}?")
            context = result.get("context", "Conversation starter")
            suggested = result.get("suggested_response", "That's an interesting question...")
            logger.info("heartbeat_done", extra={"room_id": room_id, "question": question[:50]})
            return {"question": question, "context": context, "suggested_response": suggested}
        except Exception as e:
            logger.error("heartbeat_failed", exc_info=True, extra={"room_id": room_id, "error": str(e)})
            return {
                "question": f"What's your favorite thing about {tag_str}?",
                "context": "Default fallback question",
                "suggested_response": "I really enjoy learning about this topic because...",
            }

    async def _call_llm(self, payload: dict) -> dict:
        url = f"{self._llm_base}/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

        def _sync_post():
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _sync_post)
