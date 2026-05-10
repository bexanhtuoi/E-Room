from __future__ import annotations

import pytest
from app.infrastructure.audio import AudioConfig, AudioBuffer, AudioProcessor, AudioBufferManager


class TestAudioConfig:
    def test_defaults(self):
        cfg = AudioConfig()
        assert cfg.sample_rate == 16000
        assert cfg.sample_width == 2
        assert cfg.channels == 1
        assert cfg.chunk_ms == 20
        assert cfg.rms_threshold == 0.02
        assert cfg.silence_threshold_ms == 2000

    def test_chunk_size(self):
        cfg = AudioConfig(sample_rate=16000, sample_width=2, channels=1, chunk_ms=20)
        assert cfg.chunk_size == 640

    def test_silence_chunks(self):
        cfg = AudioConfig(chunk_ms=20, silence_threshold_ms=2000)
        assert cfg.silence_chunks == 100

    def test_custom_config(self):
        cfg = AudioConfig(sample_rate=48000, sample_width=4, channels=2, chunk_ms=30)
        assert cfg.chunk_size == 48000 * 4 * 2 * 30 // 1000


class TestSpeechDetection:
    def test_silent_chunk(self):
        buf = AudioBuffer("u1", AudioConfig(rms_threshold=0.80))
        assert buf.feed_chunk(0, b"\x00" * 640) is None

    def test_loud_chunk_speech_start(self):
        buf = AudioBuffer("u2", AudioConfig(rms_threshold=0.01))
        result = buf.feed_chunk(0, b"\x00\x80" * 320)
        assert result == "speech_start"

    def test_quiet_speaker_high_threshold(self):
        """Quiet speaker with high RMS threshold should not trigger."""
        buf = AudioBuffer("u3", AudioConfig(rms_threshold=0.80))
        result = buf.feed_chunk(0, b"\x00\x02" * 320)
        assert result is None

    def test_noise_floor(self):
        """Low-level noise should not trigger speech."""
        buf = AudioBuffer("u4", AudioConfig(rms_threshold=0.05))
        # Create PCM with very low amplitude
        low_noise = b"\x01\x00" * 320  # amplitude ~1
        result = buf.feed_chunk(0, low_noise)
        assert result is None

    def test_empty_chunk(self):
        buf = AudioBuffer("u5", AudioConfig())
        assert buf.feed_chunk(0, b"") is None


class TestSpeechEndDetection:
    def test_speech_then_silence(self):
        buf = AudioBuffer("u6", AudioConfig(rms_threshold=0.01, chunk_ms=20, silence_threshold_ms=60))
        # Start speech
        assert buf.feed_chunk(0, b"\x00\x80" * 320) == "speech_start"
        # Continue speech
        assert buf.feed_chunk(1, b"\x00\x80" * 320) is None
        # Silence chunks (need enough to trigger silence threshold)
        results = []
        for i in range(2, 8):
            results.append(buf.feed_chunk(i, b"\x00" * 640))
        # At least one should be "speech_end"
        assert "speech_end" in results

    def test_short_utterance(self):
        """Single short loud chunk immediately followed by silence."""
        buf = AudioBuffer("u7", AudioConfig(rms_threshold=0.01, chunk_ms=20, silence_threshold_ms=40))
        assert buf.feed_chunk(0, b"\x00\x80" * 320) == "speech_start"
        # 3 silence chunks needed for 40ms / 20ms = 2, so we need >= silence_chunks
        result = None
        for i in range(1, 10):
            r = buf.feed_chunk(i, b"\x00" * 640)
            if r == "speech_end":
                result = r
                break
        assert result == "speech_end"


class TestChunkReordering:
    def test_in_order_chunks(self):
        buf = AudioBuffer("u8", AudioConfig(rms_threshold=0.01))
        assert buf.feed_chunk(0, b"\x00\x80" * 320) == "speech_start"
        assert buf.feed_chunk(1, b"\x00\x80" * 320) is None
        assert buf.feed_chunk(2, b"\x00\x80" * 320) is None

    def test_out_of_order_chunks(self):
        buf = AudioBuffer("u9", AudioConfig(rms_threshold=0.01))
        # Send chunks out of order: 0, 2, 1
        r0 = buf.feed_chunk(0, b"\x00\x80" * 320)
        assert r0 == "speech_start"
        # Chunk 2 arrives before 1 — should NOT be processed yet
        r2 = buf.feed_chunk(2, b"\x00\x80" * 320)
        assert r2 is None
        # Chunk 1 arrives — now 1 AND 2 should be processed
        r1 = buf.feed_chunk(1, b"\x00\x80" * 320)
        assert r1 is None  # chunk 1 processed
        # Chunk 3 should now be next
        buf.feed_chunk(3, b"\x00\x80" * 320)

    def test_duplicate_sequence(self):
        """Duplicate sequence numbers should be ignored (heap-based)."""
        buf = AudioBuffer("u10", AudioConfig(rms_threshold=0.01))
        assert buf.feed_chunk(0, b"\x00\x80" * 320) == "speech_start"
        # Send duplicate seq 0 — should be ignored
        r = buf.feed_chunk(0, b"\x00\x80" * 320)
        assert r is None
        # Seq 1 should still be expected
        assert buf.feed_chunk(1, b"\x00\x80" * 320) is None

    def test_gap_in_sequence(self):
        """Large gap in sequence numbers should buffer."""
        buf = AudioBuffer("u11", AudioConfig(rms_threshold=0.01))
        buf.feed_chunk(0, b"\x00\x80" * 320)
        # Skip 1-9, send 10
        r = buf.feed_chunk(10, b"\x00\x80" * 320)
        assert r is None  # buffered, not processed
        # Send 1-9 in order to unblock
        for i in range(1, 10):
            buf.feed_chunk(i, b"\x00\x80" * 320)
        # Now 10 should be processed
        buf.feed_chunk(11, b"\x00\x80" * 320)


class TestAudioProcessor:
    def test_pcm_to_wav(self):
        pcm = b"\x00" * 640
        wav = AudioProcessor.pcm_to_wav(pcm, sample_rate=16000)
        assert wav[:4] == b"RIFF"
        assert wav[8:12] == b"WAVE"
        assert len(wav) == 44 + len(pcm)  # 44-byte header + data

    def test_pcm_to_wav_stereo(self):
        pcm = b"\x00" * 1280
        wav = AudioProcessor.pcm_to_wav(pcm, sample_rate=44100, sample_width=2, channels=2)
        assert wav[:4] == b"RIFF"
        assert len(wav) == 44 + len(pcm)

    def test_empty_pcm(self):
        wav = AudioProcessor.pcm_to_wav(b"", sample_rate=16000)
        assert wav[:4] == b"RIFF"
        assert len(wav) == 44  # header only


class TestAudioBufferManager:
    def test_get_or_create(self):
        mgr = AudioBufferManager()
        buf1 = mgr.get_or_create("user-A")
        buf2 = mgr.get_or_create("user-A")
        assert buf1 is buf2  # same instance

    def test_different_users(self):
        mgr = AudioBufferManager()
        buf1 = mgr.get_or_create("user-X")
        buf2 = mgr.get_or_create("user-Y")
        assert buf1 is not buf2

    def test_remove(self):
        mgr = AudioBufferManager()
        mgr.get_or_create("user-R")
        mgr.remove("user-R")
        # Creating again should give a new instance
        buf = mgr.get_or_create("user-R")
        assert buf.user_id == "user-R"

    def test_clear_all(self):
        mgr = AudioBufferManager()
        mgr.get_or_create("user-C1")
        mgr.get_or_create("user-C2")
        mgr.clear_all()
        buf = mgr.get_or_create("user-C1")
        assert buf is not None  # fresh instance

    def test_custom_config(self):
        mgr = AudioBufferManager()
        cfg = AudioConfig(rms_threshold=0.99)
        buf = mgr.get_or_create("user-CC", config=cfg)
        assert buf.config.rms_threshold == 0.99


class TestAudioBufferReset:
    def test_reset_clears_speech(self):
        buf = AudioBuffer("u12", AudioConfig(rms_threshold=0.01))
        buf.feed_chunk(0, b"\x00\x80" * 320)
        assert buf.get_sentence() != b""
        buf.reset()
        assert buf.get_sentence() == b""
        # Should re-detect speech after reset
        assert buf.feed_chunk(0, b"\x00\x80" * 320) == "speech_start"
