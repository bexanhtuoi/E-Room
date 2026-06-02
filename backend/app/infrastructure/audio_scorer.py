from __future__ import annotations

import math
from typing import Any

import numpy as np


def compute_accuracy(
    expected_words: list[list[str]],
    aligned_phonemes: list[dict[str, Any]],
) -> float:
    if not aligned_phonemes:
        return 0.0
    confidences = [a["confidence"] for a in aligned_phonemes]
    return float(np.mean(confidences)) if confidences else 0.0


def compute_gop_from_alignment(aligned_phonemes: list[dict[str, Any]]) -> float:
    if not aligned_phonemes:
        return 0.0
    log_probs = [a["avg_log_prob"] for a in aligned_phonemes]
    mean_log_prob = float(np.mean(log_probs)) if log_probs else -10.0
    gop = max(0.0, min(1.0, math.exp(mean_log_prob) * 2.0))
    return gop


def compute_fluency(word_timestamps: list[dict[str, Any]]) -> float:
    if not word_timestamps or len(word_timestamps) < 2:
        return 1.0
    gaps: list[float] = []
    for i in range(1, len(word_timestamps)):
        gap = word_timestamps[i]["start"] - word_timestamps[i - 1]["end"]
        if gap > 0:
            gaps.append(gap)
    if not gaps:
        return 1.0
    mean_gap = float(np.mean(gaps))
    total_duration = word_timestamps[-1]["end"] - word_timestamps[0]["start"]
    if total_duration <= 0:
        return 1.0
    total_silence = sum(gaps)
    silence_ratio = total_silence / total_duration
    if silence_ratio > 0.5:
        fluency = 0.5 - (silence_ratio - 0.5)
    else:
        fluency = 1.0 - silence_ratio
    return max(0.0, min(1.0, fluency))


def compute_prosody(pcm_audio: bytes | np.ndarray, sample_rate: int = 16000) -> float:
    if isinstance(pcm_audio, bytes):
        audio = np.frombuffer(pcm_audio, dtype=np.int16).astype(np.float32) / 32768.0
    else:
        audio = pcm_audio.astype(np.float32)
    if len(audio) < sample_rate // 10:
        return 1.0
    frame_len = int(sample_rate * 0.025)
    hop_len = int(sample_rate * 0.010)
    num_frames = max(1, (len(audio) - frame_len) // hop_len + 1)
    energies: list[float] = []
    for i in range(num_frames):
        start = i * hop_len
        end = start + frame_len
        if end > len(audio):
            break
        frame = audio[start:end]
        energy = float(np.sqrt(np.mean(frame ** 2)))
        energies.append(energy)
    if len(energies) < 2:
        return 1.0
    energy_mean = float(np.mean(energies))
    if energy_mean < 1e-6:
        return 0.5
    energy_std = float(np.std(energies))
    energy_cv = energy_std / energy_mean if energy_mean > 0 else 0
    optimal_cv = 0.45
    bandwidth = 0.40
    prosody = max(0.0, min(1.0, math.exp(-((energy_cv - optimal_cv) ** 2) / (2 * bandwidth ** 2))))
    return prosody


def compute_pron_score(
    accuracy: float,
    gop: float,
    fluency: float,
    prosody: float,
) -> float:
    return (
        accuracy * 0.40
        + gop * 0.20
        + fluency * 0.25
        + prosody * 0.15
    )


class PronunciationScorer:

    def compute_all(
        self,
        expected_words: list[list[str]],
        aligned_phonemes: list[dict[str, Any]],
        word_timestamps: list[dict[str, Any]],
        pcm_audio: bytes | np.ndarray | None = None,
        sample_rate: int = 16000,
    ) -> dict[str, Any]:
        accuracy = compute_accuracy(expected_words, aligned_phonemes)
        gop = compute_gop_from_alignment(aligned_phonemes)
        fluency = compute_fluency(word_timestamps) if word_timestamps else 1.0
        prosody = compute_prosody(pcm_audio, sample_rate) if pcm_audio is not None else 1.0
        overall = compute_pron_score(accuracy, gop, fluency, prosody)
        return {
            "overall": round(overall * 10, 1),
            "accuracy": round(accuracy * 10, 1),
            "gop": round(gop * 10, 1),
            "fluency": round(fluency * 10, 1),
            "prosody": round(prosody * 10, 1),
        }
