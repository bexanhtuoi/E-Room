from app.ai.stt.cloud import transcribe_cloud_whisper
from app.ai.stt.dispatch import (
    STT_PROVIDERS,
    choose_stt_provider,
    transcribe_audio,
    transcribe_audio_async,
    transcribe_auto,
)
from app.ai.stt.helpers import (
    MIN_SEGMENT_LOGPROB,
    build_stt_prompt,
    convert_audio_to_float32,
    convert_audio_to_wav_bytes,
    is_loopy_hallucination,
    is_prompt_echo,
    is_repetitive_hallucination,
    normalize_pcm_int16,
    normalize_words,
    resolve_stt_language,
)
from app.ai.stt.local import get_whisper_model, transcribe_faster_whisper
from app.ai.stt.server import (
    STT_ALIVE_CACHE,
    STT_SERVER_URL_OVERRIDE_KEY,
    STT_URL_CACHE,
    STT_URL_CACHE_TTL,
    get_stt_server_url_override,
    is_stt_server_alive,
    transcribe_whisper_server,
)
from app.config import settings

__all__ = [
    "MIN_SEGMENT_LOGPROB",
    "STT_ALIVE_CACHE",
    "STT_PROVIDERS",
    "STT_SERVER_URL_OVERRIDE_KEY",
    "STT_URL_CACHE",
    "STT_URL_CACHE_TTL",
    "build_stt_prompt",
    "choose_stt_provider",
    "convert_audio_to_float32",
    "convert_audio_to_wav_bytes",
    "get_stt_server_url_override",
    "get_whisper_model",
    "is_loopy_hallucination",
    "is_prompt_echo",
    "is_repetitive_hallucination",
    "is_stt_server_alive",
    "normalize_pcm_int16",
    "normalize_words",
    "resolve_stt_language",
    "settings",
    "transcribe_audio",
    "transcribe_audio_async",
    "transcribe_auto",
    "transcribe_cloud_whisper",
    "transcribe_faster_whisper",
    "transcribe_whisper_server",
]
