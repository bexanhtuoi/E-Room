from __future__ import annotations

import json
import time
from typing import Any

from openai import AsyncOpenAI

from app.config import settings
from app.agent.prompt import HEARTBEAT_SYSTEM_TEMPLATE
from app.log import get_logger

logger = get_logger(__name__)
client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)


async def generate_heartbeat_question(room_id: str, context: str) -> dict[str, Any]:
    _t0 = time.monotonic()
    logger.info("Nhịp tim - bắt đầu tạo câu hỏi",
        extra={"room_id": room_id})

    try:
        resp = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": HEARTBEAT_SYSTEM_TEMPLATE},
                {"role": "user", "content": context or "Hãy tạo một câu hỏi thảo luận về AI."},
            ],
            temperature=0.7,
            max_tokens=256,
        )
        content = resp.choices[0].message.content or ""
        data = _parse_heartbeat_response(content)

        logger.info("Nhịp tim - tạo câu hỏi hoàn tất",
            extra={"room_id": room_id, "question": data.get("question", "")[:50],
                   "elapsed_s": round(time.monotonic() - _t0, 2)})
        return data
    except Exception as e:
        logger.error("Nhịp tim - tạo câu hỏi thất bại",
            exc_info=True, extra={"room_id": room_id, "error": str(e)})
        return {
            "question_id": "",
            "question": "Bạn nghĩ gì về tương lai của AI?",
            "answers": [],
        }


def _parse_heartbeat_response(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict) and "question" in parsed:
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass

    return {
        "question_id": str(hash(content))[:8],
        "question": content.strip(),
        "answers": [],
    }


generate_heartbeat = generate_heartbeat_question
