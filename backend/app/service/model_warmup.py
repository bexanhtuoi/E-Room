from __future__ import annotations

from app.infrastructure.audio_pipeline import PronunciationPipeline
from app.log import get_logger

log = get_logger(__name__)


async def warmup_models() -> None:
    log.info("Khởi tạo mô hình...")
    try:
        pipeline = PronunciationPipeline()
        log.info("Khởi tạo mô hình hoàn tất")
    except Exception:
        log.warning("Khởi tạo mô hình thất bại", exc_info=True)
