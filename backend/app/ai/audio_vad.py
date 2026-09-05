import time
from typing import Dict, Optional

import numpy as np

from app.config import settings
from app.log import get_logger

log = get_logger("app.ai.audio_vad")


def create_user_audio_state(user_identity: str) -> Dict:
    return {
        "user_identity": user_identity,
        "sample_rate": 16000,
        "frames": [],
        "is_speaking": False,
        "speech_start_time": None,
        "last_voice_time": None,
    }


def calculate_audio_rms(frame: np.ndarray | bytes) -> float:
    if isinstance(frame, bytes):
        frame_arr = np.frombuffer(frame, dtype=np.int16)
    else:
        frame_arr = frame

    if len(frame_arr) == 0:
        return 0.0

    if frame_arr.dtype == np.int16:
        frame_float = frame_arr.astype(np.float32) / 32768.0
    else:
        frame_float = frame_arr.astype(np.float32)

    return float(np.sqrt(np.mean(frame_float**2)))


def reset_user_audio_state(state: Dict) -> None:
    state["is_speaking"] = False
    state["speech_start_time"] = None
    state["last_voice_time"] = None
    state["frames"] = []


def finalize_speech_frames(
    state: Dict,
    min_speech_seconds: Optional[float] = None,
) -> Optional[np.ndarray]:
    min_duration = min_speech_seconds if min_speech_seconds is not None else settings.stt_vad_min_speech_seconds
    frames = state.get("frames", [])

    if not frames:
        reset_user_audio_state(state)
        return None

    full_audio = np.concatenate(frames)
    duration = len(full_audio) / state.get("sample_rate", 16000)

    reset_user_audio_state(state)

    if duration < min_duration:
        return None

    return full_audio


def process_audio_frame(
    state: Dict,
    frame_data: np.ndarray | bytes,
    energy_threshold: Optional[float] = None,
    silence_seconds: Optional[float] = None,
    min_speech_seconds: Optional[float] = None,
    max_speech_seconds: Optional[float] = None,
) -> Optional[np.ndarray]:
    threshold = energy_threshold if energy_threshold is not None else settings.stt_vad_energy_threshold
    silence_timeout = silence_seconds if silence_seconds is not None else settings.stt_vad_silence_seconds
    max_duration = max_speech_seconds if max_speech_seconds is not None else settings.stt_vad_max_speech_seconds

    if isinstance(frame_data, bytes):
        frame = np.frombuffer(frame_data, dtype=np.int16)
    else:
        frame = frame_data

    if len(frame) == 0:
        return None

    now = time.time()
    energy = calculate_audio_rms(frame)
    has_voice = energy >= threshold

    if has_voice:
        if not state["is_speaking"]:
            state["is_speaking"] = True
            state["speech_start_time"] = now
            state["frames"] = []
        state["last_voice_time"] = now
        state["frames"].append(frame)
        return None

    # Frame hien tai la silence nhung truoc do dang noi
    if state["is_speaking"]:
        state["frames"].append(frame)
        last_voice = state["last_voice_time"] or now
        speech_start = state["speech_start_time"] or now
        silence_dur = now - last_voice
        total_dur = now - speech_start

        # 1. Ngat cau khi im lang vuot nguong silence timeout
        if silence_dur >= silence_timeout:
            return finalize_speech_frames(state, min_speech_seconds=min_speech_seconds)

        # 2. Tu dong cat doan neu nguoi dung noi qua dai
        if total_dur >= max_duration:
            return finalize_speech_frames(state, min_speech_seconds=min_speech_seconds)

    return None
