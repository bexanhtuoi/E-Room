import json
import wave
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.ai.audio_vad import create_user_audio_state, process_audio_frame
from app.ai.raw_recorder import (
    RawAttemptRecorder,
    UtteranceRef,
    metadata_path,
    raw_audio_path,
)
from app.ai.transcriber import handle_speech_completion


def _voice_frame(n: int = 1600) -> np.ndarray:
    t = np.linspace(0, 0.1, n)
    return (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)


def _silence_frame(n: int = 1600) -> np.ndarray:
    return np.zeros(n, dtype=np.int16)


@pytest.fixture
def speech_dir(tmp_path, monkeypatch):
    import app.config as cfg

    monkeypatch.setattr(cfg.settings, "speech_log_dir", str(tmp_path), raising=False)
    monkeypatch.setattr(cfg.settings, "speech_log_save_audio", True, raising=False)
    monkeypatch.setattr(cfg.settings, "speech_raw_enabled", True, raising=False)
    return tmp_path


def _make_recorder(room_id=9001, user_identity="7", **kwargs) -> RawAttemptRecorder:
    defaults = dict(
        energy_threshold=0.01,
        end_silence_seconds=0.05,
        max_attempt_seconds=300.0,
        flush_bytes=4096,
        enabled=True,
    )
    defaults.update(kwargs)
    return RawAttemptRecorder(room_id=room_id, user_identity=user_identity, **defaults)


class TestRawAttemptLifecycle:
    def test_silence_only_no_attempt_created(self, speech_dir):
        rec = _make_recorder()
        for _ in range(20):
            rec.write_frame(_silence_frame())
        rec.check_limits()
        rec.close()

        assert rec.attempt_id is None
        attempts = speech_dir / "room_9001" / "attempts"
        assert not attempts.exists() or not any(attempts.iterdir())

    def test_voice_opens_attempt_and_waves_are_valid(self, speech_dir):
        rec = _make_recorder()
        for _ in range(5):
            rec.write_frame(_silence_frame())
        assert not rec.is_open

        for _ in range(10):
            rec.write_frame(_voice_frame())
        assert rec.is_open

        for _ in range(10):
            rec.write_frame(_silence_frame())
        rec.check_limits()
        assert not rec.is_open

        wav = raw_audio_path(9001, rec.attempt_id if rec.attempt_id else "")
        # attempt_id reset after close — find via attempts dir
        attempts = list((speech_dir / "room_9001" / "attempts").iterdir())
        assert len(attempts) == 1
        attempt_id = attempts[0].name
        wav = raw_audio_path(9001, attempt_id)

        with wave.open(str(wav), "rb") as w:
            assert w.getframerate() == 16000
            assert w.getnchannels() == 1
            assert w.getsampwidth() == 2
            frames = w.getnframes()
            # 10 voice + 10 silence frames, each 1600 samples = 0.1s → 2.0s
            assert frames == 10 * 1600 + 10 * 1600
            audio = np.frombuffer(w.readframes(frames), dtype=np.int16)

        # raw giữ cả speech lẫn pause
        assert np.any(audio[: 10 * 1600] != 0)
        assert np.all(audio[10 * 1600 :] == 0)

    def test_metadata_fields_complete(self, speech_dir):
        rec = _make_recorder()
        for _ in range(8):
            rec.write_frame(_voice_frame())
        rec.begin_utterance(0)
        rec.end_utterance(8 * 1600)
        for _ in range(10):
            rec.write_frame(_silence_frame())
        rec.check_limits()

        attempts = list((speech_dir / "room_9001" / "attempts").iterdir())
        assert len(attempts) == 1
        attempt_id = attempts[0].name
        meta_file = metadata_path(9001, attempt_id)
        assert meta_file.exists()

        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        assert meta["attempt_id"] == attempt_id
        assert meta["user_id"] == 7
        assert meta["room_id"] == 9001
        assert meta["sample_rate"] == 16000
        assert meta["channels"] == 1
        assert meta["raw_audio_path"] == f"attempts/{attempt_id}/raw.wav"
        assert meta["duration_sec"] == pytest.approx(1.8, abs=0.05)
        assert meta["start_sec"] == pytest.approx(0.0)
        assert meta["end_sec"] > 0
        assert meta["num_utterances"] == 1
        utt = meta["utterances"][0]
        assert utt["message_id"] is None
        assert utt["text"] is None
        assert utt["status"] == "finalized"
        assert utt["start_sample"] == 0
        assert utt["end_sample"] == 8 * 1600

    def test_multi_utterance_timestamps(self, speech_dir):
        rec = _make_recorder()
        for _ in range(6):
            rec.write_frame(_voice_frame())
        rec.begin_utterance(0)
        ref1 = rec.end_utterance(6 * 1600)

        for _ in range(4):
            rec.write_frame(_silence_frame())
        for _ in range(5):
            rec.write_frame(_voice_frame())
        rec.begin_utterance(10 * 1600)
        ref2 = rec.end_utterance(5 * 1600)

        for _ in range(10):
            rec.write_frame(_silence_frame())
        rec.check_limits()

        attempts = list((speech_dir / "room_9001" / "attempts").iterdir())
        attempt_id = attempts[0].name
        meta = json.loads(metadata_path(9001, attempt_id).read_text(encoding="utf-8"))
        assert meta["num_utterances"] == 2
        u0, u1 = meta["utterances"]
        assert u0["start_sample"] == 0
        assert u0["end_sample"] == 6 * 1600
        assert u1["start_sample"] == 10 * 1600
        assert u1["end_sample"] == 15 * 1600
        assert u1["start_sec"] > u0["end_sec"]
        assert ref1.index == 0
        assert ref2.index == 1

    def test_buffer_stays_bounded(self, speech_dir):
        rec = _make_recorder(flush_bytes=4096)
        max_seen = 0
        for _ in range(500):
            rec.write_frame(_voice_frame())
            max_seen = max(max_seen, rec.buffered_bytes)
        assert max_seen <= 4096 + 1600 * 2  # 1 frame margin
        rec.close()

    def test_memoryview_frame_supported(self, speech_dir):
        rec = _make_recorder()
        frame = memoryview(_voice_frame().tobytes())
        rec.write_frame(frame)
        assert rec.is_open
        rec.close()

    def test_attach_after_close_updates_metadata_file(self, speech_dir):
        rec = _make_recorder()
        for _ in range(5):
            rec.write_frame(_voice_frame())
        rec.begin_utterance(0)
        ref = rec.end_utterance(5 * 1600)
        for _ in range(10):
            rec.write_frame(_silence_frame())
        rec.check_limits()

        assert isinstance(ref, UtteranceRef)
        ref.attach(message_id=555, text="hello world")

        meta = json.loads(metadata_path(9001, ref.attempt_id).read_text(encoding="utf-8"))
        utt = meta["utterances"][0]
        assert utt["message_id"] == 555
        assert utt["text"] == "hello world"

    def test_attach_while_open_updates_memory_then_close_persists(self, speech_dir):
        rec = _make_recorder()
        for _ in range(5):
            rec.write_frame(_voice_frame())
        rec.begin_utterance(0)
        ref = rec.end_utterance(5 * 1600)
        ref.attach(message_id=777, text="in-memory")
        assert rec.utterances[0]["message_id"] == 777
        rec.close()

        meta = json.loads(metadata_path(9001, ref.attempt_id).read_text(encoding="utf-8"))
        assert meta["utterances"][0]["message_id"] == 777
        assert meta["utterances"][0]["text"] == "in-memory"

    def test_close_mid_utterance_marks_truncated(self, speech_dir):
        rec = _make_recorder()
        for _ in range(5):
            rec.write_frame(_voice_frame())
        rec.begin_utterance(0)
        rec.close(reason="stream_end")

        attempts = list((speech_dir / "room_9001" / "attempts").iterdir())
        meta = json.loads(metadata_path(9001, attempts[0].name).read_text(encoding="utf-8"))
        assert meta["close_reason"] == "stream_end"
        assert meta["utterances"][0]["status"] == "truncated"

    def test_disabled_recorder_is_noop(self, speech_dir):
        rec = _make_recorder(enabled=False)
        for _ in range(10):
            rec.write_frame(_voice_frame())
        rec.begin_utterance(0)
        assert rec.end_utterance(100) is None
        rec.close()
        assert not rec.is_open
        attempts_root = speech_dir / "room_9001" / "attempts"
        assert not attempts_root.exists() or not any(attempts_root.iterdir())

    def test_max_duration_closes_attempt(self, speech_dir):
        rec = _make_recorder(max_attempt_seconds=0.5, end_silence_seconds=999.0)
        for _ in range(10):
            rec.write_frame(_voice_frame())  # 1.0s > 0.5s max
        rec.check_limits()
        assert not rec.is_open
        meta_files = list((speech_dir / "room_9001" / "attempts").glob("*/metadata.json"))
        assert len(meta_files) == 1
        meta = json.loads(meta_files[0].read_text(encoding="utf-8"))
        assert meta["close_reason"] == "max_duration"

    def test_two_attempts_after_idle(self, speech_dir):
        rec = _make_recorder(end_silence_seconds=0.05)
        for _ in range(5):
            rec.write_frame(_voice_frame())
        rec.check_limits()
        for _ in range(10):
            rec.write_frame(_silence_frame())
        rec.check_limits()

        first_id = list((speech_dir / "room_9001" / "attempts").iterdir())[0].name

        for _ in range(5):
            rec.write_frame(_voice_frame())
        rec.check_limits()
        for _ in range(10):
            rec.write_frame(_silence_frame())
        rec.check_limits()

        attempts = list((speech_dir / "room_9001" / "attempts").iterdir())
        assert len(attempts) == 2
        assert attempts[0].name == first_id


class TestRecorderWithVad:
    def test_cooperates_with_real_vad_pipeline(self, speech_dir):
        rec = _make_recorder(end_silence_seconds=0.05, energy_threshold=0.01)
        state = create_user_audio_state("7")

        voice = _voice_frame(1600)
        silence = _silence_frame(1600)

        # speech segment
        for _ in range(10):
            pos_before = rec.samples_written
            was = state["is_speaking"]
            rec.write_frame(voice)
            done = process_audio_frame(
                state,
                voice,
                energy_threshold=0.01,
                silence_seconds=0.0,
                min_speech_seconds=0.05,
                max_speech_seconds=5.0,
            )
            if (not was) and state["is_speaking"]:
                rec.begin_utterance(pos_before)
            if done is not None:
                rec.end_utterance(len(done))
        assert state["is_speaking"] is True
        assert rec.is_open

        # silence → VAD finalize
        pos_before = rec.samples_written
        was = state["is_speaking"]
        rec.write_frame(silence)
        done = process_audio_frame(
            state,
            silence,
            energy_threshold=0.01,
            silence_seconds=0.0,
            min_speech_seconds=0.05,
            max_speech_seconds=5.0,
        )
        if done is not None:
            ref = rec.end_utterance(len(done))
        elif was and not state["is_speaking"]:
            rec.abandon_utterance()
        rec.check_limits()

        assert done is not None
        assert ref is not None
        assert ref.index == 0

        attempts = list((speech_dir / "room_9001" / "attempts").iterdir())
        assert len(attempts) == 1
        meta = json.loads(metadata_path(9001, attempts[0].name).read_text(encoding="utf-8"))
        assert meta["num_utterances"] == 1
        assert meta["utterances"][0]["status"] == "finalized"


class TestHandleSpeechCompletionAttach:
    @pytest.mark.asyncio
    async def test_handle_speech_completion_attaches_raw_ctx(self, speech_dir):
        rec = _make_recorder()
        for _ in range(5):
            rec.write_frame(_voice_frame())
        rec.begin_utterance(0)
        ref = rec.end_utterance(5 * 1600)
        rec.close()

        mock_room = MagicMock()
        mock_room.local_participant = MagicMock()
        mock_room.local_participant.publish_data = AsyncMock()

        stt_result = {
            "text": "hello world from raw",
            "language": "en",
            "duration": 1.0,
            "avg_logprob": -0.1,
            "confidence": 0.95,
            "words": [],
        }

        with patch(
            "app.ai.transcriber.transcribe_audio_async",
            AsyncMock(return_value=stt_result),
        ):
            await handle_speech_completion(
                room=mock_room,
                room_id=9001,
                user_identity="7",
                audio_data=np.zeros(16000, dtype=np.int16),
                raw_ctx=ref,
            )

        meta = json.loads(metadata_path(9001, ref.attempt_id).read_text(encoding="utf-8"))
        utt = meta["utterances"][0]
        assert utt["message_id"] is not None
        assert utt["text"] == "hello world from raw"
        assert mock_room.local_participant.publish_data.called
