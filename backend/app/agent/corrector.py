from __future__ import annotations

import json
import time
from typing import Any

from openai import AsyncOpenAI

from app.config import settings
from app.agent.prompt import CORRECTOR_SYSTEM_TEMPLATE
from app.log import get_logger

logger = get_logger(__name__)
client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)


async def correct_text(text: str, user_id: str, pipeline_result: dict[str, Any]) -> dict[str, Any]:
    _t0 = time.monotonic()
    logger.info("Bắt đầu sửa lỗi phát âm",
        extra={"user_id": user_id, "text": text, "text_len": len(text)})

    words = pipeline_result.get("words", [])
    aligned = pipeline_result.get("aligned_phonemes", [])
    word_context = _build_word_phoneme_context(pipeline_result.get("text", ""), words, aligned)

    user_message = (
        f"Người dùng nói: \"{text}\"\n\n"
        f"Phân tích từng từ (điểm, phát âm):\n{json.dumps(word_context, ensure_ascii=False, indent=2)}\n\n"
        f"Điểm tổng thể: {pipeline_result['scores']['overall']}/100\n"
        f"Cần sửa lỗi: {pipeline_result['needs_remediation']}\n\n"
        "Hãy đưa ra phản hồi phát âm chi tiết."
    )

    try:
        resp = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": CORRECTOR_SYSTEM_TEMPLATE},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=512,
        )
        llm_time = round(time.monotonic() - _t0, 2)
        content = resp.choices[0].message.content or ""

        result = _parse_correction_response(content, text)
        logger.info("Sửa lỗi phát âm hoàn tất",
            extra={"user_id": user_id, "text": text,
                   "llm_s": llm_time,
                   "errors_count": len(result.get("errors", [])),
                   "has_feedback": bool(result.get("pronunciation_feedback"))})
        return result
    except Exception as e:
        logger.error("Sửa lỗi phát âm thất bại",
            exc_info=True, extra={"user_id": user_id, "error": str(e)})
        return {
            "corrected": text,
            "explanation": "Không thể phân tích phát âm ngay lúc này.",
            "pronunciation_feedback": "",
            "errors": [],
            "tts_text": text,
        }


def _build_word_phoneme_context(
    text: str, words: list[dict[str, Any]], aligned: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    word_map = {w["word"].lower(): w for w in words}
    result = []
    for entry in aligned:
        word = entry.get("word", "")
        word_info = word_map.get(word.lower(), {})
        result.append({
            "word": word,
            "score": word_info.get("score", 0),
            "pronunciation": entry.get("pronunciation", ""),
            "phonemes": entry.get("phonemes", []),
            "confidence": entry.get("confidence", 0),
            "duration": entry.get("duration", 0),
        })
    return result


def _parse_correction_response(content: str, original: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return {
                "corrected": parsed.get("corrected", original),
                "explanation": parsed.get("explanation", ""),
                "pronunciation_feedback": parsed.get("pronunciation_feedback", ""),
                "errors": parsed.get("errors", []),
                "tts_text": parsed.get("tts_text", parsed.get("corrected", original)),
            }
    except (json.JSONDecodeError, TypeError):
        pass

    return {
        "corrected": original,
        "explanation": content,
        "pronunciation_feedback": "",
        "errors": [],
        "tts_text": original,
    }
