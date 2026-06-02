from __future__ import annotations

import base64
import math
import struct
import time
from collections import OrderedDict

from app.config import settings
from app.log import get_logger

logger = get_logger(__name__)


class AudioConfig:
    sample_rate: int = 16000
    sample_width: int = 2
    channels: int = 1
    silence_threshold_ms: int = 400
    rms_threshold: float = 0.04
    max_buffer_duration: int = 30


class AudioBuffer:
    def __init__(self, user_id: str, config: AudioConfig | None = None) -> None:
        self.user_id = user_id
        self.config = config or AudioConfig()
        self._pending: OrderedDict[int, bytes] = OrderedDict()
        self._last_seq: int = 0
        self._finalized: bool = False
        self._speech_segments: list[bytes] = []
        self._speech_active: bool = False
        self._last_audio_time: float = 0.0

    def push(self, seq: int, data_b64: str) -> None:
        if seq <= self._last_seq:
            logger.debug("audio_buffer_seq_trùng",
                extra={"user_id": self.user_id, "seq": seq})
            return
        pcm = base64.b64decode(data_b64)
        self._pending[seq] = pcm
        self._last_seq = seq
        self._speech_segments.append(pcm)
        self._speech_active = True
        self._last_audio_time = time.time()
        logger.debug("audio_buffer_chunk_đã_xếp_hàng",
            extra={"user_id": self.user_id, "seq": seq, "size": len(pcm), "pending": len(self._pending)})

    def _check_vad(self) -> str | None:
        if not self._speech_active:
            return None

        if not self._speech_segments:
            return None

        latest = self._speech_segments[-1]
        import struct

        samples = struct.unpack(f"<{len(latest)//2}h", latest)
        if not samples:
            return None

        import math

        rms = math.sqrt(sum(s * s for s in samples) / len(samples)) / 32768.0
        silence_ms = (time.time() - self._last_audio_time) * 1000

        if rms < self.config.rms_threshold and silence_ms > self.config.silence_threshold_ms:
            logger.debug("Phát hiện im lặng - kết thúc giọng nói",
                extra={"user_id": self.user_id, "rms": round(rms, 4), "silence_ms": round(silence_ms, 0)})
            return "speech_end"

        if rms >= self.config.rms_threshold:
            logger.debug("Phát hiện giọng nói",
                extra={"user_id": self.user_id, "rms": round(rms, 4)})
            return "speech_start"

        return None

    def check_vad(self) -> str | None:
        return self._check_vad()

    def finalize(self) -> bytes | None:
        self._speech_active = False
        if not self._speech_segments:
            return None
        pcm = b"".join(self._speech_segments)
        self._speech_segments.clear()
        logger.debug("Kết thúc thu âm",
            extra={"user_id": self.user_id, "pcm_bytes": len(pcm)})
        return pcm

    def feed_chunk(self, seq: int, pcm_bytes: bytes) -> str:
        self._pending[seq] = pcm_bytes
        self._speech_segments.append(pcm_bytes)
        self._speech_active = True
        self._last_audio_time = time.time()
        if len(self._speech_segments) > 1:
            return self._check_vad() or ""
        return ""

    def get_sentence(self) -> bytes:
        return self.finalize() or b""

    def reset(self) -> None:
        self._pending.clear()
        self._speech_segments.clear()
        self._speech_active = False
        self._finalized = False


class AudioBufferManager:
    def __init__(self) -> None:
        self._buffers: dict[str, AudioBuffer] = {}

    def get_or_create(self, user_id: str, config: AudioConfig | None = None) -> AudioBuffer:
        if user_id not in self._buffers:
            self._buffers[user_id] = AudioBuffer(user_id, config)
        return self._buffers[user_id]

    def remove(self, user_id: str) -> None:
        self._buffers.pop(user_id, None)


class AudioProcessor:
    pass
