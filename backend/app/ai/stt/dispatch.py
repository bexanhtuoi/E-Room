import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional

import numpy as np

from app.ai.stt.cloud import transcribe_cloud_whisper
from app.ai.stt.local import transcribe_faster_whisper
from app.ai.stt.server import is_stt_server_alive, transcribe_whisper_server
from app.config import settings
from app.log import get_logger

log = get_logger("app.ai.stt.dispatch")


def transcribe_audio(
    audio_data: np.ndarray | bytes,
    sample_rate: int = 16000,
    provider: Optional[str] = None,
    **kwargs: Any,
) -> Optional[Dict[str, Any]]:
    chosen_provider = (provider or settings.stt_provider).lower()
    transcribe_fn = STT_PROVIDERS.get(chosen_provider, transcribe_auto)

    # local/auto giữ language/initial_prompt (giọng cũ). cloud dùng prompt
    # cố định nên drop để khỏi lẫn.
    if transcribe_fn is transcribe_cloud_whisper:
        kwargs.pop("language", None)
        kwargs.pop("initial_prompt", None)

    return transcribe_fn(audio_data, sample_rate=sample_rate, **kwargs)


def transcribe_auto(
    audio_data: np.ndarray | bytes,
    sample_rate: int = 16000,
    **kwargs: Any,
) -> Optional[Dict[str, Any]]:
    """STT host sống -> dùng host (large-v3-turbo, GPU). Chết/giữa chừng chết
    giữa câu -> fallback whisper local (small, CPU). Không bao giờ câm."""
    if is_stt_server_alive():
        try:
            out = transcribe_whisper_server(audio_data, sample_rate=sample_rate, **kwargs)
        except Exception as error:
            log.warning("Whisper host failed mid-call, fallback local | err=%s", str(error)[:150])
            out = None
        if out:
            return out
        log.info("Whisper host trả rỗng, thử local")
    return transcribe_faster_whisper(audio_data, sample_rate=sample_rate, **kwargs)


def choose_stt_provider(provider: Optional[str], kwargs: Dict[str, Any], queued: int) -> Optional[str]:

    name = (provider or settings.stt_provider).lower()
    # auto được tính như whisper_server khi host đang sống (tràn cloud khi tắc),
    # như local khi host chết (không tràn).
    effective = "whisper_server" if (name == "auto" and is_stt_server_alive()) else name
    if (
        queued >= 4
        and effective in ("whisper_server", "faster_whisper", "local")
        and str((kwargs or {}).get("language") or "en").lower() == "en"
        and settings.stt_cloud_api_key
    ):
        log.info("STT overflow to cloud | queued=%s", queued)
        return "cloud"
    return provider


async def transcribe_audio_async(
    audio_data: np.ndarray | bytes,
    sample_rate: int = 16000,
    provider: Optional[str] = None,
    **kwargs: Any,
) -> Optional[Dict[str, Any]]:
    loop = asyncio.get_running_loop()
    queued = stt_executor._work_queue.qsize()
    if queued >= 4:
        log.warning("STT executor congested | queued=%s", queued)
    provider = choose_stt_provider(provider, kwargs, queued)
    call = functools.partial(
        transcribe_audio,
        audio_data,
        sample_rate=sample_rate,
        provider=provider,
        **kwargs,
    )
    return await loop.run_in_executor(stt_executor, call)


stt_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="stt_worker")


STT_PROVIDERS: Dict[str, Callable] = {
    "auto": transcribe_auto,
    "faster_whisper": transcribe_faster_whisper,
    "local": transcribe_faster_whisper,
    "whisper_server": transcribe_whisper_server,
    "server": transcribe_whisper_server,
    "openai": transcribe_cloud_whisper,
    "groq": transcribe_cloud_whisper,
    "cloud": transcribe_cloud_whisper,
    "custom_api": transcribe_cloud_whisper,
}

