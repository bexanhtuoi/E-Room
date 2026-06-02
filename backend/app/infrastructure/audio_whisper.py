from __future__ import annotations

from faster_whisper import WhisperModel

from app.log import get_logger

logger = get_logger(__name__)

whisper_model = WhisperModel(
    "base",
    device="cpu",
    compute_type="default",
)

logger.info("Đã tải mô hình Faster Whisper",
    extra={"model": "base", "device": "cpu"})
