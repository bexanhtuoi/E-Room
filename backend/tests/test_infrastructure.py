from __future__ import annotations

import array
import math
import struct

import pytest

from app.infrastructure.audio import (
    AudioBuffer,
    AudioBufferManager,
    AudioConfig,
    AudioProcessor,
    _compute_rms,
)


def make_pcm(sample_values: list[int], sample_width: int = 2) -> bytes:
    fmt = {1: "b", 2: "h", 4: "i"}[sample_width]
    return struct.pack(f"<{len(sample_values)}{fmt}", *sample_values)


def make_chunk(value: int, num_samples: int = 320, sample_width: int = 2) -> bytes:
    return make_pcm([value] * num_samples, sample_width)


class TestComputeRMS:
    def test_silent_pcm_returns_near_zero(self) -> None:
        pcm = make_chunk(0, 320)
        rms = _compute_rms(pcm, 2)
        assert rms == 0.0

    def test_loud_pcm_returns_high_rms(self) -> None:
        pcm = make_chunk(5000, 320)
        rms = _compute_rms(pcm, 2)
        assert rms > 0.05

    def test_empty_pcm_returns_zero(self) -> None:
        assert _compute_rms(b"", 2) == 0.0

    def test_single_byte_pcm(self) -> None:
        pcm = bytes([50, 226, 10, 251])
        rms = _compute_rms(pcm, 1)
        assert rms > 0.0

    def test_four_byte_pcm(self) -> None:
        pcm = make_pcm([100000, -50000, 200000, -80000], 4)
        rms = _compute_rms(pcm, 4)
        assert 0.0 < rms < 1.0

    def test_unknown_sample_width_falls_back(self) -> None:
        pcm = make_chunk(2000, 160, 2)
        rms = _compute_rms(pcm, 3)
        assert rms > 0.0


class TestAudioConfig:
    def test_default_chunk_size(self) -> None:
        config = AudioConfig()
        assert config.chunk_size == 640

    def test_chunk_size_with_custom_rate(self) -> None:
        config = AudioConfig(sample_rate=48000, chunk_ms=30)
        assert config.chunk_size == 48000 * 2 * 1 * 30 // 1000

    def test_silence_chunks_from_threshold(self) -> None:
        config = AudioConfig(silence_threshold_ms=3000, chunk_ms=20)
        assert config.silence_chunks == 150

    def test_custom_values_stored(self) -> None:
        config = AudioConfig(
            sample_rate=8000,
            sample_width=1,
            channels=2,
            rms_threshold=0.05,
            silence_threshold_ms=1000,
        )
        assert config.sample_rate == 8000
        assert config.sample_width == 1
        assert config.channels == 2
        assert config.rms_threshold == 0.05
        assert config.silence_threshold_ms == 1000


class TestAudioBufferSpeechDetection:
    @pytest.fixture
    def buf(self) -> AudioBuffer:
        return AudioBuffer("test-user")

    def test_loud_chunk_triggers_speech_start(self, buf: AudioBuffer) -> None:
        result = buf.feed_chunk(0, make_chunk(8000))
        assert result == "speech_start"

    def test_silent_chunk_before_speech_returns_none(self, buf: AudioBuffer) -> None:
        result = buf.feed_chunk(0, make_chunk(10))
        assert result is None

    def test_silence_after_speech_ends_speech(self, buf: AudioBuffer) -> None:
        assert buf.feed_chunk(0, make_chunk(8000)) == "speech_start"
        for seq in range(1, 101):
            result = buf.feed_chunk(seq, make_chunk(0))
            if result == "speech_end":
                break
        assert result == "speech_end"

    def test_duplicate_sequence_is_ignored(self, buf: AudioBuffer) -> None:
        buf.feed_chunk(0, make_chunk(8000))
        result = buf.feed_chunk(0, make_chunk(8000))
        assert result is None

    def test_out_of_order_chunks_reordered(self, buf: AudioBuffer) -> None:
        buf.feed_chunk(1, make_chunk(5000))
        buf.feed_chunk(2, make_chunk(5000))
        result = buf.feed_chunk(0, make_chunk(8000))
        assert result == "speech_start"

    def test_get_sentence_returns_buffered_data(self, buf: AudioBuffer) -> None:
        chunk = make_chunk(8000)
        buf.feed_chunk(0, chunk)
        sentence = buf.get_sentence()
        assert len(sentence) == len(chunk)

    def test_sentence_cleared_after_get(self, buf: AudioBuffer) -> None:
        buf.feed_chunk(0, make_chunk(8000))
        buf.get_sentence()
        assert buf.get_sentence() == b""

    def test_reset_clears_all_state(self, buf: AudioBuffer) -> None:
        buf.feed_chunk(0, make_chunk(8000))
        buf.reset()
        assert len(buf._sentence) == 0
        assert buf._speaking is False
        assert buf._silent_chunks == 0
        assert len(buf._pending) == 0
        assert buf._next_seq == 0
        assert len(buf._seen_sequences) == 0


class TestAudioProcessor:
    def test_pcm_to_wav_produces_valid_header(self) -> None:
        pcm = make_chunk(1000, 500)
        wav = AudioProcessor.pcm_to_wav(pcm)
        assert wav[:4] == b"RIFF"
        assert wav[8:12] == b"WAVE"
        assert wav[12:16] == b"fmt "
        assert b"data" in wav[36:40]

    def test_pcm_to_wav_correct_total_length(self) -> None:
        pcm = make_chunk(0, 200)
        wav = AudioProcessor.pcm_to_wav(pcm)
        assert len(wav) == 44 + len(pcm)

    def test_pcm_to_wav_chunk_size_in_header(self) -> None:
        pcm = make_chunk(0, 100)
        wav = AudioProcessor.pcm_to_wav(pcm)
        chunk_size = struct.unpack_from("<I", wav, 4)[0]
        assert chunk_size == 36 + len(pcm)

    def test_pcm_to_wav_empty_pcm(self) -> None:
        wav = AudioProcessor.pcm_to_wav(b"")
        assert len(wav) == 44
        data_size = struct.unpack_from("<I", wav, 40)[0]
        assert data_size == 0

    def test_pcm_to_wav_custom_sample_rate(self) -> None:
        pcm = make_chunk(0, 50)
        wav = AudioProcessor.pcm_to_wav(pcm, sample_rate=44100)
        sample_rate = struct.unpack_from("<I", wav, 24)[0]
        assert sample_rate == 44100

    def test_pcm_to_wav_custom_channels(self) -> None:
        pcm = make_chunk(0, 100)
        wav = AudioProcessor.pcm_to_wav(pcm, channels=2)
        channels = struct.unpack_from("<H", wav, 22)[0]
        assert channels == 2

    def test_pcm_to_wav_bits_per_sample(self) -> None:
        pcm = make_chunk(0, 30, sample_width=1)
        wav = AudioProcessor.pcm_to_wav(pcm, sample_width=1)
        bits = struct.unpack_from("<H", wav, 34)[0]
        assert bits == 8


class TestAudioBufferManager:
    def test_get_or_create_returns_same_buffer(self) -> None:
        mgr = AudioBufferManager()
        buf1 = mgr.get_or_create("user-1")
        buf2 = mgr.get_or_create("user-1")
        assert buf1 is buf2

    def test_get_or_create_different_users_different_buffers(self) -> None:
        mgr = AudioBufferManager()
        buf1 = mgr.get_or_create("user-1")
        buf2 = mgr.get_or_create("user-2")
        assert buf1 is not buf2

    def test_remove_deletes_buffer(self) -> None:
        mgr = AudioBufferManager()
        mgr.get_or_create("user-1")
        mgr.remove("user-1")
        assert "user-1" not in mgr._buffers

    def test_remove_nonexistent_is_safe(self) -> None:
        mgr = AudioBufferManager()
        mgr.remove("ghost-user")

    def test_clear_all_removes_everything(self) -> None:
        mgr = AudioBufferManager()
        mgr.get_or_create("user-1")
        mgr.get_or_create("user-2")
        mgr.clear_all()
        assert len(mgr._buffers) == 0
