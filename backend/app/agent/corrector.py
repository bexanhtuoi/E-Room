from __future__ import annotations

import os
from typing import Any

import requests
import asyncio

from app.agent.prompt import CORRECTOR_SYSTEM_TEMPLATE
from app.log import get_logger

logger = get_logger(__name__)


class AgentCorrector:
    """AI agent that corrects grammar and pronunciation for English learners."""

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

    async def correct(self, text: str, user_id: str) -> dict[str, Any]:
        """Correct the given English text and return errors with explanations."""
        logger.info("corrector_start", extra={"user_id": user_id, "text_len": len(text)})

        payload = {
            "model": self._llm_model,
            "messages": [
                {"role": "system", "content": CORRECTOR_SYSTEM_TEMPLATE},
                {"role": "user", "content": text},
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }

        try:
            result = await self._call_llm(payload)
            logger.info("corrector_done", extra={"user_id": user_id, "errors": len(result.get("errors", []))})
            return result
        except Exception as e:
            logger.error("corrector_failed", exc_info=True, extra={"user_id": user_id, "error": str(e)})
            return {
                "corrected": text,
                "errors": [],
                "score": 10,
                "explanation": f"Correction unavailable: {e}",
            }

    async def _call_llm(self, payload: dict) -> dict:
        url = f"{self._llm_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        def _sync_post():
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return content if isinstance(content, dict) else __import__("json").loads(content)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _sync_post)
