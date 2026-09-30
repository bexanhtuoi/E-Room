from typing import Any, Dict, List, Optional

import numpy as np

from app.ai.stt.helpers import (
    MIN_SEGMENT_LOGPROB,
    build_stt_prompt,
    convert_audio_to_float32,
    is_prompt_echo,
    is_repetitive_hallucination,
    resolve_stt_language,
)
from app.config import settings
from app.log import get_logger

log = get_logger("app.ai.stt.local")

whisper_model_instance = None


def get_whisper_model():
    global whisper_model_instance

    if whisper_model_instance is None:
        from faster_whisper import WhisperModel

        log.info(
            "Loading faster-whisper model | model=%s device=%s compute=%s threads=%s beam=%s",
            settings.stt_model_size,
            settings.stt_device,
            settings.stt_compute_type,
            settings.stt_cpu_threads,
            settings.stt_beam_size,
        )

        whisper_model_instance = WhisperModel(
            settings.stt_model_size,
            device=settings.stt_device,
            compute_type=settings.stt_compute_type,
            cpu_threads=settings.stt_cpu_threads,
        )

        log.info("Faster-whisper model loaded successfully")
    return whisper_model_instance


def collect_transcript_segments(segments) -> tuple:
    full_text_list: List[str] = []

    word_timings: List[Dict[str, Any]] = []

    total_logprob = 0.0

    segment_count = 0

    for segment in segments:
        text_clean = segment.text.strip()

        if not text_clean:
            continue

        if segment.avg_logprob < MIN_SEGMENT_LOGPROB:
            log.info(
                "Dropping low-confidence segment | logprob=%.2f text='%s'",
                segment.avg_logprob,
                text_clean[:80],
            )

            continue

        full_text_list.append(text_clean)

        total_logprob += segment.avg_logprob

        segment_count += 1

        if segment.words:
            for word_info in segment.words:
                word_timings.append(
                    {
                        "word": word_info.word.strip(),
                        "start": word_info.start,
                        "end": word_info.end,
                        "probability": word_info.probability,
                    }
                )

    return full_text_list, word_timings, total_logprob, segment_count


def transcribe_faster_whisper(
    audio_data: np.ndarray | bytes,
    sample_rate: int = 16000,
    model_override: Optional[Any] = None,
    language: Optional[str] = None,
    initial_prompt: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if not settings.stt_local_enabled:
        return None

    try:
        audio = convert_audio_to_float32(audio_data)

        min_samples = int(sample_rate * settings.stt_vad_min_speech_seconds)

        if len(audio) < min_samples:
            return None

        model = model_override or get_whisper_model()

        resolved_language = resolve_stt_language(language)

        resolved_prompt = initial_prompt or build_stt_prompt(resolved_language)

        transcribe_kwargs: Dict[str, Any] = {
            "beam_size": settings.stt_beam_size,
            "temperature": 0.0,
            "initial_prompt": resolved_prompt,
            "word_timestamps": True,
        }

        if resolved_language in ("en", "vi"):
            transcribe_kwargs["language"] = resolved_language

        segments, info = model.transcribe(
            audio,
            **transcribe_kwargs,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=False,
            compression_ratio_threshold=2.4,
            no_speech_threshold=0.6,
        )

        full_text_list, word_timings, total_logprob, segment_count = collect_transcript_segments(segments)

        if not full_text_list:
            return None

        full_text = " ".join(full_text_list)

        if is_repetitive_hallucination(full_text):
            log.info("Dropping repetitive hallucination | text='%s'", full_text[:80])

            return None

        if is_prompt_echo(full_text, resolved_prompt):
            log.info("Dropping prompt echo | text='%s'", full_text[:80])

            return None

        avg_logprob = (total_logprob / segment_count) if segment_count > 0 else -1.0

        confidence = float(min(max((avg_logprob + 2.0) / 2.0, 0.0), 1.0))

        return {
            "text": full_text,
            "language": info.language,
            "duration": float(info.duration),
            "avg_logprob": float(avg_logprob),
            "confidence": confidence,
            "words": word_timings,
            "provider": "faster_whisper",
        }
    except Exception as error:
        log.error("faster-whisper error: %s", error)

        return None

