from pathlib import Path
from typing import Optional

from app.log import get_logger

log = get_logger("app.ai.stt.audio_store")

S3_PREFIX = "s3:"

SPEECH_PREFIX = "speech"


def is_s3_ref(ref: Optional[str]) -> bool:
    return isinstance(ref, str) and ref.startswith(S3_PREFIX)


def object_name_for_utterance(room_id: int, filename: str) -> str:
    return f"{SPEECH_PREFIX}/room_{room_id}/audio/{filename}"


def object_name_for_attempt(room_id: int, attempt_id: str) -> str:
    return f"{SPEECH_PREFIX}/room_{room_id}/attempts/{attempt_id}/raw.wav"


def put_audio(object_name: str, wav_bytes: bytes) -> Optional[str]:
    try:
        from app.integration.minio import put_object

        put_object(object_name, wav_bytes, content_type="audio/wav")

        return f"{S3_PREFIX}{object_name}"
    except Exception as error:
        log.warning("MinIO audio upload failed | object=%s err=%s", object_name, str(error)[:150])

        return None


def fetch_audio_bytes(room_id: int, ref: Optional[str]) -> Optional[bytes]:
    if not ref:
        return None

    if is_s3_ref(ref):
        try:
            from app.integration.minio import get_object

            return get_object(ref[len(S3_PREFIX):])
        except Exception as error:
            log.warning("MinIO audio download failed | ref=%s err=%s", ref, str(error)[:150])

            return None

    try:
        from app.ai.stt.speech_log import room_dir

        candidate = room_dir(room_id) / ref

        return candidate.read_bytes() if candidate.exists() else None
    except Exception as error:
        log.warning("Local audio read failed | ref=%s err=%s", ref, str(error)[:150])

        return None


def has_audio(room_id: int, ref: Optional[str]) -> bool:
    if not ref:
        return False

    if is_s3_ref(ref):
        return True

    try:
        from app.ai.stt.speech_log import room_dir

        return (room_dir(room_id) / ref).exists()
    except Exception:
        return False


def materialize_temp_wav(data: bytes) -> Path:
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(data)

        return Path(tmp.name)
