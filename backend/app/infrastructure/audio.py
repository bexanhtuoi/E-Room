from __future__ import annotations

import array
import heapq
import math
import struct
from collections import defaultdict
from typing import Any


class AudioConfig:
    def __init__(
        self,
        sample_rate: int = 16000,
        sample_width: int = 2,
        channels: int = 1,
        chunk_ms: int = 20,
        rms_threshold: float = 0.02,
        silence_threshold_ms: int = 2000,
    ) -> None:
        self.sample_rate = sample_rate
        self.sample_width = sample_width
        self.channels = channels
        self.chunk_ms = chunk_ms
        self.rms_threshold = rms_threshold
        self.silence_threshold_ms = silence_threshold_ms

    @property
    def chunk_size(self) -> int:
        return self.sample_rate * self.sample_width * self.channels * self.chunk_ms // 1000

    @property
    def silence_chunks(self) -> int:
        return self.silence_threshold_ms // self.chunk_ms


class AudioBuffer:
    def __init__(self, user_id: str, config: AudioConfig | None = None) -> None:
        self.user_id = user_id
        self.config = config or AudioConfig()
        self._sentence: bytearray = bytearray()
        self._speaking: bool = False
        self._silent_chunks: int = 0
        self._pending: list[tuple[int, bytes]] = []
        self._next_seq: int = 0
        self._seen_sequences: set[int] = set()

    def feed_chunk(self, seq: int, pcm: bytes) -> str | None:
        if seq in self._seen_sequences:
            return None
        self._seen_sequences.add(seq)

        heapq.heappush(self._pending, (seq, pcm))

        result: str | None = None
        while self._pending and self._pending[0][0] == self._next_seq:
            _, chunk = heapq.heappop(self._pending)
            self._next_seq += 1
            detect = self._process_chunk(chunk)
            if detect:
                result = detect
        return result

    def _process_chunk(self, pcm: bytes) -> str | None:
        if not pcm:
            return None
        rms = _compute_rms(pcm, self.config.sample_width)
        if rms >= self.config.rms_threshold:
            self._sentence.extend(pcm)
            self._silent_chunks = 0
            if not self._speaking:
                self._speaking = True
                return "speech_start"
            return None
        if self._speaking:
            self._silent_chunks += 1
            self._sentence.extend(pcm)
            if self._silent_chunks >= self.config.silence_chunks:
                self._speaking = False
                return "speech_end"
        return None

    def get_sentence(self) -> bytes:
        return bytes(self._sentence)

    def reset(self) -> None:
        self._sentence = bytearray()
        self._speaking = False
        self._silent_chunks = 0
        self._pending.clear()
        self._next_seq = 0
        self._seen_sequences.clear()


class AudioBufferManager:
    def __init__(self) -> None:
        self._buffers: dict[str, AudioBuffer] = {}

    def get_or_create(self, user_id: str, config: AudioConfig | None = None) -> AudioBuffer:
        if user_id not in self._buffers:
            self._buffers[user_id] = AudioBuffer(user_id, config)
        return self._buffers[user_id]

    def remove(self, user_id: str) -> None:
        self._buffers.pop(user_id, None)

    def clear_all(self) -> None:
        self._buffers.clear()


class AudioProcessor:
    @staticmethod
    def pcm_to_wav(
        pcm: bytes,
        sample_rate: int = 16000,
        sample_width: int = 2,
        channels: int = 1,
    ) -> bytes:
        byte_rate = sample_rate * sample_width * channels
        block_align = sample_width * channels
        data_size = len(pcm)
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + data_size,
            b"WAVE",
            b"fmt ",
            16,
            1,
            channels,
            sample_rate,
            byte_rate,
            block_align,
            sample_width * 8,
            b"data",
            data_size,
        )
        return header + pcm


def _compute_rms(pcm: bytes, sample_width: int) -> float:
    if not pcm:
        return 0.0
    count = len(pcm) // sample_width
    if count == 0:
        return 0.0
    if sample_width == 2:
        samples = array.array("h", pcm)
    elif sample_width == 1:
        samples = array.array("b", pcm)
    elif sample_width == 4:
        samples = array.array("i", pcm)
    else:
        samples = array.array("h", pcm)
    sum_sq = sum(float(s) * float(s) for s in samples[:count])
    rms = math.sqrt(sum_sq / count)
    max_val = float(1 << (sample_width * 8 - 1))
    return rms / max_val if max_val > 0 else 0.0
