import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

WAV_HEADER_SIZE = 44


def wav_header(data_size: int, sample_rate: int, channels: int, bits: int = 16) -> bytes:
    byte_rate = sample_rate * channels * bits // 8

    block_align = channels * bits // 8

    return struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits,
        b"data",
        data_size,
    )


def attempts_root(room_id: int) -> Path:
    from app.ai.stt.speech_log import room_dir

    path = room_dir(room_id) / "attempts"

    path.mkdir(parents=True, exist_ok=True)

    return path


def attempt_dir(room_id: int, attempt_id: str) -> Path:
    path = attempts_root(room_id) / attempt_id

    path.mkdir(parents=True, exist_ok=True)

    return path


def metadata_path(room_id: int, attempt_id: str) -> Path:
    return attempt_dir(room_id, attempt_id) / "metadata.json"


def raw_audio_path(room_id: int, attempt_id: str) -> Path:
    return attempt_dir(room_id, attempt_id) / "raw.wav"


def resolve_user_id(user_identity: str) -> Optional[int]:
    try:
        return int(str(user_identity))
    except (TypeError, ValueError):
        return None


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

