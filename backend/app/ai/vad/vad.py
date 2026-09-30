import time
from typing import Dict, Optional

import numpy as np

from app.ai.stt.helpers import normalize_pcm_int16
from app.ai.vad.helpers import trim_trailing_silence
from app.config import settings
from app.log import get_logger

log = get_logger("app.ai.vad")

SILERO_WINDOW_SAMPLES = 512

SILERO_SPEECH_PAD_MS = 100

_silero_model = None

_silero_failed = False


def get_silero_model():
    global _silero_model, _silero_failed

    if _silero_failed:
        return None

    if _silero_model is None:
        try:
            from silero_vad import load_silero_vad

            _silero_model = load_silero_vad(onnx=True)

            log.info("Silero VAD model loaded (onnx)")
        except Exception as error:
            _silero_failed = True

            log.warning("Silero VAD unavailable | err=%s", str(error)[:150])

    return _silero_model


def create_user_audio_state(user_identity: str) -> Dict:
    return {
        "user_identity": user_identity,
        "sample_rate": 16000,
        "frames": [],
        "is_speaking": False,
        "speech_start_time": None,
        "last_voice_time": None,
        "vad_buffer": np.zeros(0, dtype=np.int16),
        "vad_iterator": None,
        "speech_chunks": [],
    }


def reset_user_audio_state(state: Dict) -> None:
    state["is_speaking"] = False

    state["speech_start_time"] = None

    state["last_voice_time"] = None

    state["frames"] = []

    state["vad_buffer"] = np.zeros(0, dtype=np.int16)

    state["vad_iterator"] = None

    state["speech_chunks"] = []


def finalize_speech_frames(
    state: Dict,
    min_speech_seconds: Optional[float] = None,
) -> Optional[np.ndarray]:
    min_duration = min_speech_seconds if min_speech_seconds is not None else settings.stt_vad_min_speech_seconds

    frames = state.get("frames", [])

    if not frames:
        reset_user_audio_state(state)

        return None

    sample_rate = state.get("sample_rate", 16000)

    full_audio = np.concatenate(frames)

    full_audio = trim_trailing_silence(full_audio, sample_rate=sample_rate)

    duration = len(full_audio) / sample_rate

    reset_user_audio_state(state)

    if duration < min_duration:
        return None

    return full_audio


def process_audio_frame(
    state: Dict,
    frame_data: np.ndarray | bytes,
    silence_seconds: Optional[float] = None,
    min_speech_seconds: Optional[float] = None,
    max_speech_seconds: Optional[float] = None,
) -> Optional[np.ndarray]:
    frame = normalize_pcm_int16(frame_data)

    if len(frame) == 0:
        return None

    now = time.time()

    model = get_silero_model()

    if model is None:
        return None

    if state.get("vad_iterator") is None:
        from silero_vad import VADIterator

        silence_ms = int(
            (silence_seconds if silence_seconds is not None else settings.stt_vad_silence_seconds) * 1000
        )

        state["vad_iterator"] = VADIterator(
            model,
            threshold=settings.stt_vad_threshold,
            sampling_rate=16000,
            min_silence_duration_ms=silence_ms,
            speech_pad_ms=SILERO_SPEECH_PAD_MS,
        )

    max_duration = max_speech_seconds if max_speech_seconds is not None else settings.stt_vad_max_speech_seconds

    iterator = state["vad_iterator"]

    buffered = np.concatenate([state.get("vad_buffer", np.zeros(0, dtype=np.int16)), frame])

    while len(buffered) >= SILERO_WINDOW_SAMPLES:
        window = buffered[:SILERO_WINDOW_SAMPLES]

        buffered = buffered[SILERO_WINDOW_SAMPLES:]

        window_float = window.astype(np.float32) / 32768.0

        try:
            event = iterator(window_float, return_seconds=False)
        except Exception as error:
            log.warning("Silero infer failed, keep buffering | err=%s", str(error)[:120])

            continue

        if event is None:
            if state["is_speaking"]:
                state["speech_chunks"].append(window)

            continue

        if "start" in event:
            state["is_speaking"] = True

            state["speech_start_time"] = now

            state["speech_chunks"] = [window]

            continue

        if "end" in event and state["is_speaking"]:
            state["speech_chunks"].append(window)

            state["frames"] = state["speech_chunks"]

            return finalize_speech_frames(state, min_speech_seconds=min_speech_seconds)

    state["vad_buffer"] = buffered

    if state["is_speaking"]:
        speech_start = state["speech_start_time"] or now

        if now - speech_start >= max_duration:
            state["frames"] = state["speech_chunks"]

            return finalize_speech_frames(state, min_speech_seconds=min_speech_seconds)

    return None
