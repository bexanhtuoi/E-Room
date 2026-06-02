from __future__ import annotations

import asyncio
import json
import time

from app.agent.corrector import correct_text
from app.infrastructure.audio_pipeline import PronunciationPipeline
from app.infrastructure.redis_client import get_redis_client
from app.log import get_logger
from app.model import MessageType
from app.ws.auth import now
from app.ws.messages import save_message

log = get_logger(__name__)
_correction_semaphore = asyncio.Semaphore(1)


async def process_speech(pcm_data: bytes, user_id: str, room_id: str) -> None:
    _t0 = time.monotonic()
    pcm_secs = round(len(pcm_data) / 16000 / 2, 2)
    log.info("Bắt đầu xử lý giọng nói",
        extra={"user_id": user_id, "room_id": room_id, "pcm_bytes": len(pcm_data), "pcm_seconds": pcm_secs})
    try:
        pipeline = PronunciationPipeline()

        log.info("Bắt đầu phân tích giọng nói",
            extra={"user_id": user_id, "room_id": room_id})
        result = await pipeline.assess(pcm_data)
        timing = result.get("timing", {})
        text = (result["text"] or "").strip()
        scores = result["scores"]
        needs_remediation = result["needs_remediation"]
        words = result.get("words", [])
        aligned = result.get("aligned_phonemes", [])
        elapsed_assess = round(time.monotonic() - _t0, 2)
        log.info("Phân tích giọng nói hoàn tất",
            extra={"user_id": user_id, "room_id": room_id,
                   "text": text, "word_count": len(words),
                   "overall_score": scores["overall"],
                   "needs_remediation": needs_remediation,
                   "transcribe_s": timing.get("transcribe_s"),
                   "total_s": timing.get("total_s"),
                   "elapsed_s": elapsed_assess})

        if not text:
            log.info("Bỏ qua đoạn ghi âm trống",
                extra={"user_id": user_id, "room_id": room_id, "elapsed_s": elapsed_assess})
            return

        try:
            save_message(room_id, user_id, text, MessageType.TRANSCRIPT, "You")
        except Exception:
            log.warning("Lưu transcript vào DB thất bại", exc_info=True)

        payload = {
            "text": text,
            "user_id": user_id,
            "scores": scores,
            "needs_remediation": needs_remediation,
            "words": words,
            "aligned_phonemes": aligned,
        }

        try:
            client = get_redis_client()
            client.publish("room:transcript", json.dumps({
                "room_id": room_id, "user_id": user_id, **payload
            }, default=str))
            elapsed_pub = round(time.monotonic() - _t0, 2)
            log.info("Đã gửi transcript qua Redis",
                extra={"user_id": user_id, "room_id": room_id, "text_len": len(text), "elapsed_s": elapsed_pub})
        except Exception:
            log.warning("Gửi transcript qua Redis thất bại", exc_info=True)

        if needs_remediation and scores.get("overall", 10) < 7:
            log.info("Bắt đầu sửa lỗi phát âm",
                extra={"user_id": user_id, "room_id": room_id, "text": text})
            async with _correction_semaphore:
                elapsed_before_correction = round(time.monotonic() - _t0, 2)
                correction = await correct_text(text, user_id, payload)
                corrected_text = correction.get("corrected", "")
                elapsed_correction = round(time.monotonic() - _t0, 2)
                log.info("Sửa lỗi phát âm hoàn tất",
                    extra={"user_id": user_id, "room_id": room_id,
                           "corrected": corrected_text,
                           "errors_count": len(correction.get("errors", [])),
                           "wait_s": elapsed_before_correction,
                           "correction_s": elapsed_correction - elapsed_before_correction,
                           "total_s": elapsed_correction})

                try:
                    client = get_redis_client()
                    client.publish("room:correction", json.dumps({
                        "room_id": room_id, "user_id": user_id,
                        "original": text, "created_at": now(), **correction
                    }, default=str))
                    log.info("Đã gửi kết quả sửa lỗi qua Redis",
                        extra={"user_id": user_id, "room_id": room_id})
                except Exception:
                    log.warning("Gửi kết quả sửa lỗi qua Redis thất bại", exc_info=True)

                if corrected_text:
                    try:
                        save_message(
                            room_id, None, corrected_text, MessageType.AI_CORRECTION,
                            extra_payload={
                                "original": text,
                                "explanation": correction.get("explanation", ""),
                                "pronunciation_feedback": correction.get("pronunciation_feedback", ""),
                                "errors": correction.get("errors", []),
                                "tts_text": correction.get("tts_text", corrected_text),
                            },
                        )
                    except Exception:
                        log.warning("Lưu kết quả sửa lỗi vào DB thất bại", exc_info=True)
        else:
            log.info("Bỏ qua bước sửa lỗi (điểm phát âm đạt yêu cầu)",
                extra={"user_id": user_id, "room_id": room_id, "overall_score": scores["overall"]})
    except Exception:
        log.warning("Xử lý giọng nói thất bại", exc_info=True,
            extra={"user_id": user_id, "room_id": room_id})
