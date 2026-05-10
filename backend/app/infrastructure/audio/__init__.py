from __future__ import annotations

import heapq
import threading
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    sample_width: int = 2
    channels: int = 1
    chunk_ms: int = 20
    rms_threshold: float = 0.02
    silence_threshold_ms: int = 2000
    max_buffer_ms: int = 30000

    @property
    def chunk_size(self) -> int:
        return int(self.sample_rate * self.sample_width * self.channels * self.chunk_ms / 1000)

    @property
    def silence_chunks(self) -> int:
        return max(1, self.silence_threshold_ms // self.chunk_ms)


class AudioBuffer:
    """Per-user audio buffer with RMS-based speech detection and sequence ordering."""

    def __init__(self, user_id: str, config: AudioConfig) -> None:
        self.user_id = user_id
        self.config = config
        self._buffer: bytearray = bytearray()
        self._speaking = False
        self._silent_chunks = 0
        self._seq_heap: list[tuple[int, bytes]] = []
        self._next_seq = 0
        self._lock = threading.Lock()

    def feed_chunk(self, seq: int, pcm: bytes) -> Optional[str]:
        """Feed a PCM chunk. Returns 'speech_start', 'speech_end', or None."""
        import array
        with self._lock:
            expected = self._next_seq
            self._push_ordered(seq, pcm)
            if expected != seq:
                return None
            return self._process_chunk(pcm)

    def _push_ordered(self, seq: int, pcm: bytes) -> None:
        if seq >= self._next_seq:
            heapq.heappush(self._seq_heap, (seq, pcm))
        while self._seq_heap and self._seq_heap[0][0] == self._next_seq:
            _, data = heapq.heappop(self._seq_heap)
            self._next_seq += 1

    def _process_chunk(self, pcm: bytes) -> Optional[str]:
        if not self._speaking:
            if self._detect_speech(pcm):
                self._speaking = True
                self._silent_chunks = 0
                self._buffer.extend(pcm)
                return "speech_start"
        else:
            if self._detect_speech(pcm):
                self._silent_chunks = 0
            else:
                self._silent_chunks += 1
            self._buffer.extend(pcm)
            if self._silent_chunks >= self.config.silence_chunks:
                self._speaking = False
                self._silent_chunks = 0
                return "speech_end"
        return None

    def _detect_speech(self, pcm: bytes) -> bool:
        import array
        import math
        if len(pcm) < 2:
            return False
        samples = array.array("h")
        samples.frombytes(pcm)
        if len(samples) == 0:
            return False
        rms = math.sqrt(sum(s * s for s in samples) / len(samples)) / 32768.0
        return rms > self.config.rms_threshold

    def get_sentence(self) -> bytes:
        with self._lock:
            data = bytes(self._buffer)
            self._buffer = bytearray()
            return data

    def reset(self) -> None:
        with self._lock:
            self._buffer = bytearray()
            self._speaking = False
            self._silent_chunks = 0
            self._seq_heap.clear()
            self._next_seq = 0


class AudioProcessor:
    """Convert raw PCM to WAV format."""

    @staticmethod
    def pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000, sample_width: int = 2, channels: int = 1) -> bytes:
        import struct
        byte_rate = sample_rate * sample_width * channels
        block_align = sample_width * channels
        data_size = len(pcm_data)
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + data_size, b"WAVE", b"fmt ", 16, 1,
            channels, sample_rate, byte_rate, block_align, sample_width * 8,
            b"data", data_size,
        )
        return header + pcm_data


class AudioBufferManager:
    """Thread-safe manager for multiple user audio buffers."""

    def __init__(self) -> None:
        self._buffers: dict[str, AudioBuffer] = {}
        self._lock = threading.Lock()

    def get_or_create(self, user_id: str, config: AudioConfig | None = None) -> AudioBuffer:
        with self._lock:
            if user_id not in self._buffers:
                self._buffers[user_id] = AudioBuffer(user_id, config or AudioConfig())
            return self._buffers[user_id]

    def remove(self, user_id: str) -> None:
        with self._lock:
            self._buffers.pop(user_id, None)

    def clear_all(self) -> None:
        with self._lock:
            self._buffers.clear()
