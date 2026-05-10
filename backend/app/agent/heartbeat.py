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

    @staticmethod
    def _heartbeat_style(count: int) -> str:
        if count == 1:
            return "icebreaker, light, fun, easy to answer"
        elif count == 2:
            return "deeper, thought-provoking, encourages personal reflection"
        return "challenging, hypothetical, opinion-based, or speculative"

    @staticmethod
    def _build_user_prompt(
        topic: str,
        tag_str: str,
        recent_messages: list[dict] | None,
        heartbeat_count: int,
    ) -> str:
        last_msgs = recent_messages[-5:] if recent_messages else []
        msg_summary = "\n".join([
            f"{m.get('user_name', 'User')}: {m.get('content', '')[:100]}"
            for m in last_msgs
        ])

        style = AgentHeartbeat._heartbeat_style(heartbeat_count)

        return f"""Room topic: {topic or "English conversation"}
Interests: {tag_str}
Recent messages (last 5):
{msg_summary or "No recent messages."}
Heartbeat number: {heartbeat_count}
Desired style: {style}

Generate a JSON object with:
- "question": the question to ask
- "context": why this question fits
- "suggested_response": a sample answer"""

    @staticmethod
    def _build_heartbeat_result(result: dict, tag_str: str) -> dict[str, Any]:
        return {
            "question": result.get("question", f"What do you think about {tag_str}?"),
            "context": result.get("context", "Conversation starter"),
            "suggested_response": result.get(
                "suggested_response", "That's an interesting question..."
            ),
        }

    async def generate(
        self,
        room_id: str,
        topic: str,
        tags: list[str] | None = None,
        recent_messages: list[dict] | None = None,
        heartbeat_count: int = 1,
    ) -> dict[str, Any]:
        logger.info("heartbeat_start", extra={"room_id": room_id, "heartbeat_count": heartbeat_count})

        tag_str = ", ".join(tags) if tags else "general English"
        user_prompt = self._build_user_prompt(topic, tag_str, recent_messages, heartbeat_count)

        payload = {
            "model": self._llm_model,
            "messages": [
                {"role": "system", "content": HEARTBEAT_SYSTEM_TEMPLATE},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.8,
            "response_format": {"type": "json_object"},
        }

        try:
            result = await self._call_llm(payload)
            response = self._build_heartbeat_result(result, tag_str)
            logger.info("heartbeat_done", extra={"room_id": room_id, "question": response["question"][:50]})
            return response
        except Exception as e:
            logger.error("heartbeat_failed", exc_info=True, extra={"room_id": room_id, "error": str(e)})
            return self._build_heartbeat_result({}, tag_str)

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
