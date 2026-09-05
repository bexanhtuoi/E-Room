import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.ai.audio_vad import (
    calculate_audio_rms,
    create_user_audio_state,
    finalize_speech_frames,
    process_audio_frame,
)
from app.ai.stt import (
    convert_audio_to_float32,
    convert_audio_to_wav_bytes,
    transcribe_audio,
    transcribe_cloud_whisper,
    transcribe_faster_whisper,
)
from app.ai.transcriber import (
    build_transcript_payload,
    handle_speech_completion,
)


class TestAudioVADFunctions:
    def test_calculate_rms(self):
        silence = np.zeros(320, dtype=np.int16)
        assert calculate_audio_rms(silence) == 0.0

        t = np.linspace(0, 0.02, 320)
        sine = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)
        rms = calculate_audio_rms(sine)
        assert rms > 0.1

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
        mock_segment = MagicMock()
        mock_segment.text = " Hello world from Vietnam "
        mock_segment.avg_logprob = -0.18
        mock_segment.words = [
            MagicMock(word="Hello", start=0.0, end=0.5, probability=0.95),
            MagicMock(word="world", start=0.5, end=1.0, probability=0.92),
        ]
        mock_info = MagicMock(language="en", duration=1.5)

        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], mock_info)

        # 1s audio
        audio = np.zeros(16000, dtype=np.int16)
        result = transcribe_faster_whisper(audio, sample_rate=16000, model_override=mock_model)

        assert result is not None
        assert result["text"] == "Hello world from Vietnam"
        assert result["language"] == "en"
        assert result["duration"] == 1.5
        assert result["confidence"] > 0.8
        assert len(result["words"]) == 2

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
    async def test_handle_speech_completion_broadcast_and_at_ai(self):
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
            patch("app.ai.transcriber.transcribe_audio_async", AsyncMock(return_value=sample_stt_result)),
            patch("app.ai.tasks.enqueue_ai_job") as mock_enqueue_ai,
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

            # Check @ai trigger
            assert mock_enqueue_ai.called
            mock_enqueue_ai.assert_called_once()
            args = mock_enqueue_ai.call_args[0]
            assert args[0] == 1
            assert args[1] == "answer"
            assert args[2] == "explain dependency inversion"
