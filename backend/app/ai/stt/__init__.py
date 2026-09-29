from app.ai.stt import providers as providers_module
from app.ai.stt.helpers import (
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
from app.ai.stt.providers import (
    STT_PROVIDERS,
    choose_stt_provider,
    get_stt_server_url_override,
    get_whisper_model,
    is_stt_server_alive,
    settings,
    transcribe_audio,
    transcribe_audio_async,
    transcribe_auto,
    transcribe_cloud_whisper,
    transcribe_faster_whisper,
    transcribe_whisper_server,
)

_STT_ALIVE_CACHE = providers_module._STT_ALIVE_CACHE
_STT_URL_CACHE = providers_module._STT_URL_CACHE

__all__ = [
    "STT_PROVIDERS",
    "_STT_ALIVE_CACHE",
    "_STT_URL_CACHE",
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
