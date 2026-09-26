"""Per-user speech logs cho E-Room.

Mỗi câu user nói (sau STT) được append vào 1 file JSONL riêng:

    <SPEECH_LOG_DIR>/room_<room_id>/user_<user_id>.jsonl

Mỗi dòng = 1 utterance:
{
  "message_id": 123,          # id trong bảng messages (None nếu chưa lưu DB)
  "room_id": 1,
  "user_id": 5,
  "user_name": "An",
  "text": "hello everyone...",        # STT raw
  "corrected_text": "hello everyone...",  # user sửa tay, mặc định = text
  "language": "en",
  "duration": 2.1,
  "confidence": 0.93,
  "avg_logprob": -0.2,
  "words": [...],
  "provider": "faster_whisper",
  "audio_file": "audio/user_5_123.wav",  # relative path, None nếu tắt lưu audio
  "pronunciation": null,  # filled bởi app.ai.pronunciation
  "created_at": "2026-...Z",
  "edited_at": null
}

File này là nguồn cho 2 tính năng tương lai:
1. `summary` — đọc toàn bộ room (mọi user, sort theo created_at).
2. User tự sửa lại những gì mình đã nói (corrected_text).
3. AI chấm phát âm (wav2vec2 + thuật toán khác) đọc audio_file + text.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.log import get_logger

log = get_logger("app.ai.speech_log")

_DEFAULT_DIR = Path(__file__).resolve().parent.parent.parent / "log" / "speech"


def get_speech_log_dir() -> Path:
    from app.config import settings

    configured = getattr(settings, "speech_log_dir", "") or os.getenv("SPEECH_LOG_DIR", "")
    base = Path(configured) if configured else _DEFAULT_DIR
    if not base.is_absolute():
        # Resolve relative từ backend/ root
        base = Path(__file__).resolve().parent.parent.parent / base
    base.mkdir(parents=True, exist_ok=True)
    return base


def should_save_audio() -> bool:
    from app.config import settings

    flag = getattr(settings, "speech_log_save_audio", True)
    if isinstance(flag, str):
        return flag.lower() in ("true", "1", "yes")
    return bool(flag)


def room_dir(room_id: int) -> Path:
    path = get_speech_log_dir() / f"room_{room_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def user_log_path(room_id: int, user_id: Any) -> Path:
    uid = user_id if user_id is not None else "unknown"
    return room_dir(room_id) / f"user_{uid}.jsonl"


def user_audio_dir(room_id: int) -> Path:
    path = room_dir(room_id) / "audio"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_utterance_audio(
    room_id: int,
    user_id: Any,
    message_id: Any,
    audio_data,
    sample_rate: int = 16000,
) -> Optional[str]:
    """Lưu wav 16k mono cho 1 utterance. Trả về relative path hoặc None."""
    if not should_save_audio() or audio_data is None:
        return None
    try:
        from app.ai.stt import convert_audio_to_wav_bytes

        wav_bytes = convert_audio_to_wav_bytes(audio_data, sample_rate=sample_rate)
        uid = user_id if user_id is not None else "unknown"
        mid = message_id if message_id is not None else int(datetime.now(timezone.utc).timestamp() * 1000)
        filename = f"user_{uid}_{mid}.wav"
        dest = user_audio_dir(room_id) / filename
        dest.write_bytes(wav_bytes)
        return f"audio/{filename}"
    except Exception as error:
        log.warning("Could not save utterance audio | room=%s user=%s err=%s", room_id, user_id, error)
        return None


def append_utterance(
    room_id: int,
    user_id: Optional[int],
    user_name: str,
    message_id: Optional[int],
    text: str,
    language: str = "en",
    duration: float = 0.0,
    confidence: float = 1.0,
    avg_logprob: float = 0.0,
    words: Optional[List[Dict[str, Any]]] = None,
    provider: str = "whisper_server",
    audio_data=None,
    sample_rate: int = 16000,
) -> Dict[str, Any]:
    """Append 1 utterance vào file JSONL của user. Không raise (best-effort)."""
    audio_file = save_utterance_audio(room_id, user_id, message_id, audio_data, sample_rate)
    entry: Dict[str, Any] = {
        "message_id": message_id,
        "room_id": room_id,
        "user_id": user_id,
        "user_name": user_name,
        "text": text,
        "corrected_text": text,
        "language": language,
        "duration": float(duration or 0.0),
        "confidence": float(confidence),
        "avg_logprob": float(avg_logprob),
        "words": words or [],
        "words_count": len(words or []),
        "provider": provider,
        "audio_file": audio_file,
        "pronunciation": None,
        "feedback": None,
        "created_at": _utcnow_iso(),
        "edited_at": None,
    }
    try:
        path = user_log_path(room_id, user_id)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as error:
        log.warning("Could not append speech log | room=%s user=%s err=%s", room_id, user_id, error)
    return entry


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    entries: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def read_user_log(room_id: int, user_id: Any) -> List[Dict[str, Any]]:
    return _read_jsonl(user_log_path(room_id, user_id))


def list_room_users(room_id: int) -> List[str]:
    """Trả về danh sách user_id (dạng str) đã có log trong room."""
    directory = room_dir(room_id)
    users: List[str] = []
    for child in directory.glob("user_*.jsonl"):
        stem = child.stem  # user_<id>
        users.append(stem[len("user_") :])
    return sorted(users)


def read_room_logs(room_id: int) -> Dict[str, List[Dict[str, Any]]]:
    return {uid: read_user_log(room_id, uid) for uid in list_room_users(room_id)}


def get_room_transcript_for_summary(room_id: int) -> List[Dict[str, Any]]:
    """Gộp mọi user, sort theo created_at — dùng cho mục summary sau này.

    Ưu tiên `corrected_text` (bản user đã sửa) thay vì STT raw.
    """
    merged: List[Dict[str, Any]] = []
    for entries in read_room_logs(room_id).values():
        merged.extend(entries)
    merged.sort(key=lambda e: str(e.get("created_at", "")))
    return [
        {
            "message_id": e.get("message_id"),
            "user_id": e.get("user_id"),
            "user_name": e.get("user_name"),
            "text": e.get("corrected_text") or e.get("text"),
            "raw_text": e.get("text"),
            "language": e.get("language"),
            "duration": e.get("duration"),
            "confidence": e.get("confidence"),
            "pronunciation": e.get("pronunciation"),
            "feedback": e.get("feedback"),
            "created_at": e.get("created_at"),
        }
        for e in merged
    ]


def update_corrected_text(
    room_id: int,
    user_id: Any,
    message_id: int,
    corrected_text: str,
) -> Optional[Dict[str, Any]]:
    """User sửa lại câu mình đã nói. Ghi đè file JSONL. Trả về entry mới hoặc None.

    Quy ước chấm điểm raw -> sửa -> chấm:
    - whisper lúc nào cũng lưu raw với pronunciation=None (xem append_utterance),
    - chỉ POST .../score mới gắn điểm, và điểm luôn chấm trên corrected_text,
    - nếu user sửa text SAU khi đã có điểm, điểm + feedback cũ bị reset về None
      để bắt chấm lại — tránh điểm của bản cũ dính sang bản mới.
    """
    path = user_log_path(room_id, user_id)
    entries = _read_jsonl(path)
    updated: Optional[Dict[str, Any]] = None
    now = _utcnow_iso()
    for entry in entries:
        if entry.get("message_id") == message_id:
            if entry.get("corrected_text") != corrected_text:
                entry["corrected_text"] = corrected_text
                entry["edited_at"] = now
                entry["pronunciation"] = None
                entry["feedback"] = None
            updated = entry
            break
    if updated is None:
        return None
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    tmp.replace(path)
    return updated


def attach_pronunciation(
    room_id: int,
    user_id: Any,
    message_id: int,
    score: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Gắn kết quả chấm phát âm vào 1 utterance."""
    path = user_log_path(room_id, user_id)
    entries = _read_jsonl(path)
    updated: Optional[Dict[str, Any]] = None
    for entry in entries:
        if entry.get("message_id") == message_id:
            entry["pronunciation"] = score
            updated = entry
            break
    if updated is None:
        return None
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    tmp.replace(path)
    return updated


def attach_feedback(
    room_id: int,
    user_id: Any,
    message_id: int,
    feedback: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Gắn nhận xét AI vào 1 utterance (chỉ sau khi đã có pronunciation.report)."""
    path = user_log_path(room_id, user_id)
    entries = _read_jsonl(path)
    updated: Optional[Dict[str, Any]] = None
    for entry in entries:
        if entry.get("message_id") == message_id:
            entry["feedback"] = feedback
            updated = entry
            break
    if updated is None:
        return None
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    tmp.replace(path)
    return updated


def resolve_audio_path(room_id: int, audio_file: Optional[str]) -> Optional[Path]:
    if not audio_file:
        return None
    candidate = room_dir(room_id) / audio_file
    return candidate if candidate.exists() else None
