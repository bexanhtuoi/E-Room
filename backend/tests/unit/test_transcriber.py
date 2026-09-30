import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.ai.vad.audio_vad import (
    calculate_audio_rms,
    create_user_audio_state,
    finalize_speech_frames,
    process_audio_frame,
    trim_trailing_silence,
)
from app.ai.stt import (
    build_stt_prompt,
    choose_stt_provider,
    convert_audio_to_float32,
    convert_audio_to_wav_bytes,
    is_loopy_hallucination,
    is_prompt_echo,
    is_repetitive_hallucination,
    resolve_stt_language,
    transcribe_audio,
    transcribe_audio_async,
    transcribe_cloud_whisper,
    transcribe_whisper_server,
)
from app.ai.stt.completion import build_transcript_payload, handle_speech_completion
from app.ai.stt.transcriber import cancel_user_stream
from app.repositories.message import is_recent_duplicate, message_crud


def make_loud_frame(n: int = 1600) -> np.ndarray:
    t = np.linspace(0, 0.1, n)
    return (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)


class TestAudioVADFunctions:
    def test_calculate_rms(self):
        silence = np.zeros(320, dtype=np.int16)
        assert calculate_audio_rms(silence) == 0.0

        t = np.linspace(0, 0.02, 320)
        sine = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)
        rms = calculate_audio_rms(sine)
        assert rms > 0.1

    def test_memoryview_frame_from_livekit(self):
        # LiveKit tra event.frame.data dang memoryview — phai xu ly duoc,
        # khong duoc crash nhu truoc (AttributeError: dtype).
        state = create_user_audio_state("user1")
        loud = memoryview(make_loud_frame().tobytes())

        assert process_audio_frame(state, loud) is None
        assert state["is_speaking"] is True

        quiet = memoryview(np.zeros(1600, dtype=np.int16).tobytes())
        done = process_audio_frame(
            state,
            quiet,
            silence_seconds=0.0,
            min_speech_seconds=0.05,
        )
        assert done is not None
        assert len(done) > 0

    def test_calculate_rms_memoryview_matches_array(self):
        sine = make_loud_frame()
        assert calculate_audio_rms(memoryview(sine.tobytes())) == pytest.approx(
            calculate_audio_rms(sine)
        )

    def test_trim_trailing_silence_keeps_speech(self):
        speech = make_loud_frame(16000)
        silence = np.zeros(32000, dtype=np.int16)
        clip = np.concatenate([speech, silence])

        trimmed = trim_trailing_silence(clip)

        assert len(trimmed) < len(clip)
        assert len(trimmed) >= len(speech)
        assert len(trimmed) <= len(speech) + 16000 * 0.25 + 320

    def test_trim_all_silence_returns_empty(self):
        silence = np.zeros(16000, dtype=np.int16)
        assert len(trim_trailing_silence(silence)) == 0

    def test_finalize_trims_silence_before_duration_check(self):
        state = create_user_audio_state("user1")
        state["frames"] = [make_loud_frame(16000), np.zeros(32000, dtype=np.int16)]

        done = finalize_speech_frames(state, min_speech_seconds=0.5)

        assert done is not None
        assert len(done) < 48000

    def test_converters_accept_memoryview(self):
        sine = make_loud_frame()
        view = memoryview(sine.tobytes())

        floats = convert_audio_to_float32(view)
        assert floats.dtype == np.float32
        assert len(floats) == len(sine)

        wav = convert_audio_to_wav_bytes(view)
        assert wav[:4] == b"RIFF"

    def test_process_audio_frame_vad_lifecycle(self):
        state = create_user_audio_state("user123")

        t = np.linspace(0, 0.02, 320)
        voice_frame = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)
        silence_frame = np.zeros(320, dtype=np.int16)

        # 1. Noi 10 frames (0.2s)
        for _ in range(10):
            res = process_audio_frame(
                state,
                voice_frame,
                energy_threshold=0.01,
                silence_seconds=0.1,
                min_speech_seconds=0.1,
                max_speech_seconds=5.0,
            )
            assert res is None
        assert state["is_speaking"] is True

        # 2. Im lang qua 0.1s
        time.sleep(0.12)
        res = process_audio_frame(
            state,
            silence_frame,
            energy_threshold=0.01,
            silence_seconds=0.1,
            min_speech_seconds=0.1,
            max_speech_seconds=5.0,
        )
        assert res is not None
        assert len(res) >= 3200
        assert state["is_speaking"] is False

    def test_finalize_too_short_audio_returns_none(self):
        state = create_user_audio_state("user123")
        state["frames"].append(np.zeros(160, dtype=np.int16))  # 0.01s
        result = finalize_speech_frames(state, min_speech_seconds=0.5)
        assert result is None


class TestSTTFunctions:
    def test_convert_audio_to_float32(self):
        int16_arr = np.array([0, 32767, -32768], dtype=np.int16)
        float_arr = convert_audio_to_float32(int16_arr)
        assert float_arr.dtype == np.float32
        assert float_arr[0] == 0.0
        assert np.isclose(float_arr[1], 1.0, atol=1e-3)
        assert np.isclose(float_arr[2], -1.0, atol=1e-3)

    def test_convert_audio_to_wav_bytes(self):
        audio = np.zeros(16000, dtype=np.int16)
        wav_bytes = convert_audio_to_wav_bytes(audio, sample_rate=16000)
        assert len(wav_bytes) > 44  # WAV header is 44 bytes
        assert wav_bytes[:4] == b"RIFF"
        assert wav_bytes[8:12] == b"WAVE"

    def test_transcribe_faster_whisper_with_mock_model(self):
        # Local model đã xóa — test server parse verbose_json thay thế.
        payload = {
            "text": "Hello world from Vietnam",
            "language": "en",
            "duration": 1.5,
            "segments": [
                {
                    "avg_logprob": -0.18,
                    "words": [
                        {"word": "Hello", "start": 0.0, "end": 0.5, "probability": 0.95},
                        {"word": "world", "start": 0.5, "end": 1.0, "probability": 0.92},
                    ],
                }
            ],
        }
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = payload

        audio = np.zeros(16000, dtype=np.int16)
        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response
            result = transcribe_whisper_server(audio, sample_rate=16000, language="en")

        assert result is not None
        assert result["text"] == "Hello world from Vietnam"
        assert result["language"] == "en"
        assert result["duration"] == 1.5
        assert result["confidence"] > 0.8
        assert len(result["words"]) == 2

    def test_repetitive_hallucination_guard(self):
        assert is_repetitive_hallucination("thank you thank you thank you thank you") is True
        assert is_repetitive_hallucination("yes yes yes yes yes") is True
        assert is_repetitive_hallucination("hello world from Vietnam") is False
        assert is_repetitive_hallucination("yes yes") is False

    def test_loopy_hallucination_partial_repeat(self):
        # DB that: cum 4 tu lap lai nhung ca cau khong lap y hét
        assert is_loopy_hallucination("Nó có một cái mồm đáng màu à? Đáng màu hả? Nó có một cái mồm đáng màu à?") is True
        assert is_repetitive_hallucination("Nó có một cái mồm đáng màu à? Đáng màu hả? Nó có một cái mồm đáng màu à?") is True
        assert is_loopy_hallucination("Hello everyone, I am Hoang and I am 20 years old.") is False
        assert is_loopy_hallucination("Hello, how are you today?") is False

    def test_prompt_echo_guard(self):
        auto_prompt = build_stt_prompt("auto")
        assert is_prompt_echo("Transcribe exactly what is said, word for word.", auto_prompt) is True
        assert is_prompt_echo("Transcribe exactly what is said, word for word. Transcribe exactly what is said,", auto_prompt) is True
        assert is_prompt_echo("Hello everyone, welcome to the morning lab.", auto_prompt) is False
        assert is_prompt_echo("What is said?", auto_prompt) is False

    def test_transcribe_drops_prompt_echo(self):
        echo_text = build_stt_prompt("auto")
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {"text": echo_text, "language": "en", "duration": 2.0, "segments": []}

        audio = np.zeros(32000, dtype=np.int16)
        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response
            assert transcribe_whisper_server(audio, sample_rate=16000, language="auto") is None

    def test_transcribe_drops_repetitive_hallucination(self):
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {
            "text": "thank you thank you thank you thank you",
            "language": "en",
            "duration": 2.0,
            "segments": [],
        }

        audio = np.zeros(32000, dtype=np.int16)
        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response
            assert transcribe_whisper_server(audio, sample_rate=16000) is None

    def test_transcribe_cloud_whisper_success(self):
        audio = np.zeros(16000, dtype=np.int16)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "text": "Hello from Groq Cloud Whisper",
            "language": "en",
            "duration": 1.0,
            "words": [{"word": "Hello", "start": 0.0, "end": 0.5}],
        }

        with patch("httpx.Client.post", return_value=mock_response):
            result = transcribe_cloud_whisper(
                audio_data=audio,
                api_key="gsk_fake_key",
                base_url="https://api.groq.com/openai/v1",
                model_name="whisper-large-v3",
            )
            assert result is not None
            assert result["text"] == "Hello from Groq Cloud Whisper"
            assert result["provider"] == "cloud_whisper-large-v3"
            assert len(result["words"]) == 1

    def test_transcribe_dispatcher_switch(self):
        audio = np.zeros(16000, dtype=np.int16)

        with patch.dict("app.ai.stt.STT_PROVIDERS", {"groq": MagicMock(return_value={"text": "cloud text"})}):
            res = transcribe_audio(audio, provider="groq")
            assert res == {"text": "cloud text"}

    def test_cloud_whisper_tolerates_null_words(self):
        audio = np.zeros(16000, dtype=np.int16)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "hello", "language": "en", "duration": 1.0, "words": None}

        with patch("httpx.Client.post", return_value=mock_response):
            result = transcribe_cloud_whisper(audio_data=audio, api_key="key", base_url="http://x/v1")

        assert result is not None
        assert result["text"] == "hello"
        assert result["words"] == []

    def test_dispatcher_registers_custom_api(self):
        from app.ai import stt as stt_module

        assert stt_module.STT_PROVIDERS["custom_api"] is transcribe_cloud_whisper

    def test_resolve_stt_language_order(self):
        assert resolve_stt_language("vi") == "vi"
        assert resolve_stt_language("AUTO") == "auto"
        assert resolve_stt_language("xx") == "en"
        assert resolve_stt_language(None) == "en"

    def test_build_stt_prompt_per_language(self):
        assert "Vietnamese learners" in build_stt_prompt("en")
        # Prompt Viet phai CO DAU — whisper bat chuoc chinh ta cua prompt.
        assert "tiếng Việt" in build_stt_prompt("vi")
        assert build_stt_prompt("auto") == build_stt_prompt("xx")

    def test_faster_whisper_auto_omits_language_param(self):
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {"text": "xin chao", "language": "vi", "duration": 1.0, "segments": []}

        audio = np.zeros(16000, dtype=np.int16)
        with patch("httpx.Client") as mock_client_cls:
            post = mock_client_cls.return_value.__enter__.return_value.post
            post.return_value = mock_response
            result = transcribe_whisper_server(audio, sample_rate=16000, language="auto")

        assert result is not None and result["text"] == "xin chao"
        _, kwargs = post.call_args
        assert "language" not in kwargs.get("data", {})

    def test_faster_whisper_pins_language_param(self):
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {"text": "xin chao", "language": "vi", "duration": 1.0, "segments": []}

        audio = np.zeros(16000, dtype=np.int16)
        with patch("httpx.Client") as mock_client_cls:
            post = mock_client_cls.return_value.__enter__.return_value.post
            post.return_value = mock_response
            result = transcribe_whisper_server(audio, sample_rate=16000, language="vi")

        assert result is not None and result["text"] == "xin chao"
        _, kwargs = post.call_args
        assert kwargs["data"]["language"] == "vi"
        assert "tiếng Việt" in kwargs["data"]["prompt"]

    def test_overflow_valve_routes_english_to_cloud(self):
        # Patch dung settings object ma choose_stt_provider dang doc
        # (test_ai_timeout reload app.config nen app.config.settings co the
        # la object khac — khong duoc doc ambient state o day).
        import app.ai.stt as stt_module

        stt_settings = stt_module.settings
        with patch.object(stt_settings, "stt_cloud_api_key", ""):
            assert choose_stt_provider(None, {"language": "en"}, 5) is None
        with patch.object(stt_settings, "stt_cloud_api_key", "gsk_test"):
            assert choose_stt_provider(None, {"language": "en"}, 17) == "cloud"
            assert choose_stt_provider(None, {"language": "vi"}, 17) is None
            assert choose_stt_provider(None, {"language": "auto"}, 17) is None
            assert choose_stt_provider(None, {"language": "en"}, 0) is None
            assert choose_stt_provider("groq", {"language": "en"}, 17) == "groq"

    @pytest.mark.asyncio
    async def test_async_forwards_language_kwarg(self):
        audio = np.zeros(16000, dtype=np.int16)
        with patch("app.ai.stt.dispatch.transcribe_audio", return_value={"text": "hi"}) as mock_sync:
            result = await transcribe_audio_async(audio, language="vi")
            assert result == {"text": "hi"}
            _, kwargs = mock_sync.call_args
            assert kwargs.get("language") == "vi"


class TestTranscriberFunctions:
    def test_build_transcript_payload(self):
        payload_str = build_transcript_payload(
            message_id=10,
            room_id=1,
            user_id=5,
            user_name="Alice",
            text="Hello guys",
            confidence=0.95,
            duration=1.2,
        )
        data = json.loads(payload_str)
        assert data["type"] == "transcript"
        assert data["message_id"] == 10
        assert data["user_name"] == "Alice"
        assert data["text"] == "Hello guys"
        assert data["is_final"] is True

    @pytest.mark.asyncio
    async def test_handle_speech_completion_broadcast_without_voice_ai_trigger(self):
        mock_room = MagicMock()
        mock_room.local_participant = MagicMock()
        mock_room.local_participant.publish_data = AsyncMock()

        sample_stt_result = {
            "text": "@ai explain dependency inversion",
            "language": "en",
            "duration": 2.0,
            "avg_logprob": -0.1,
            "confidence": 0.95,
            "words": [],
        }

        with (
            patch("app.ai.stt.completion.transcribe_audio_async", AsyncMock(return_value=sample_stt_result)),
            patch("app.tasks.room_jobs.enqueue_ai_job") as mock_enqueue_ai,
        ):
            audio_data = np.zeros(16000 * 2, dtype=np.int16)
            await handle_speech_completion(
                room=mock_room,
                room_id=1,
                user_identity="1",
                audio_data=audio_data,
            )

            # Check publish_data
            assert mock_room.local_participant.publish_data.called
            call_args = mock_room.local_participant.publish_data.call_args[0][0]
            payload = json.loads(call_args)
            assert payload["type"] == "transcript"
            assert payload["text"] == "@ai explain dependency inversion"

            # Voice transcript never triggers AI — only chat does.
            assert not mock_enqueue_ai.called

    def test_cancel_user_stream_replaces_old_pipeline(self):
        old_task = MagicMock()
        old_task.done.return_value = False
        registry = {"7": old_task}

        cancel_user_stream(registry, "7")

        old_task.cancel.assert_called_once()
        assert "7" not in registry

    def test_cancel_user_stream_ignores_missing_or_done(self):
        done_task = MagicMock()
        done_task.done.return_value = True
        registry = {"7": done_task}

        cancel_user_stream(registry, "7")
        done_task.cancel.assert_not_called()

        cancel_user_stream(registry, "nobody")

    def test_transcribe_drops_low_confidence_segment(self):
        # Server path: logprob thap -> van tra text nhung confidence ~0.
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {
            "text": "Genteel. No. No.",
            "language": "en",
            "duration": 2.0,
            "segments": [{"avg_logprob": -2.5, "words": []}],
        }

        audio = np.zeros(32000, dtype=np.int16)
        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response
            result = transcribe_whisper_server(audio, sample_rate=16000)

        assert result is not None
        assert result["confidence"] == pytest.approx(0.0)

    def test_save_transcript_drops_recent_duplicate(self):
        import uuid

        from sqlmodel import Session

        from app.database import engine

        text = f"dupe guard {uuid.uuid4().hex[:8]}"
        first_id, _, _ = message_crud.save_transcript(
            room_id=424242,
            user_identity="nobody",
            text=text,
            duration=1.0,
            confidence=0.9,
            avg_logprob=-0.2,
            words_count=2,
        )
        assert first_id is not None

        second_id, _, _ = message_crud.save_transcript(
            room_id=424242,
            user_identity="nobody",
            text=text,
            duration=1.0,
            confidence=0.9,
            avg_logprob=-0.2,
            words_count=2,
        )
        assert second_id is None

        with Session(engine) as db:
            assert is_recent_duplicate(db, 424242, None, text) is True
            assert is_recent_duplicate(db, 424242, None, "something else entirely") is False
