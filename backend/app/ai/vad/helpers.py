from typing import Optional

import numpy as np

from app.ai.stt.helpers import normalize_pcm_int16
from app.config import settings

TRIM_FRAME_SAMPLES = 320

TRIM_PAD_SECONDS = 0.25


def calculate_audio_rms(frame: np.ndarray | bytes) -> float:
    frame_arr = normalize_pcm_int16(frame)

    if len(frame_arr) == 0:
        return 0.0

    if frame_arr.dtype == np.int16:
        frame_float = frame_arr.astype(np.float32) / 32768.0
    else:
        frame_float = frame_arr.astype(np.float32)

    return float(np.sqrt(np.mean(frame_float**2)))


def trim_trailing_silence(
    audio: np.ndarray,
    sample_rate: int = 16000,
    energy_threshold: Optional[float] = None,
    pad_seconds: float = TRIM_PAD_SECONDS,
) -> np.ndarray:
    if len(audio) == 0:
        return audio

    threshold = energy_threshold if energy_threshold is not None else settings.stt_vad_energy_threshold

    last_voice_end = 0

    for start in range(0, len(audio), TRIM_FRAME_SAMPLES):
        window = audio[start:start + TRIM_FRAME_SAMPLES]

        if calculate_audio_rms(window) >= threshold:
            last_voice_end = min(start + TRIM_FRAME_SAMPLES, len(audio))

    if last_voice_end == 0:
        return np.zeros(0, dtype=np.int16)

    pad_samples = int(pad_seconds * sample_rate)

    return audio[: min(len(audio), last_voice_end + pad_samples)]
