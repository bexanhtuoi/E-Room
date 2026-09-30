import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.ai.stt.helpers import normalize_pcm_int16
from app.ai.stt.paths import attempt_dir, attempts_root, metadata_path, raw_audio_path, resolve_user_id, utcnow_iso, wav_header
from app.ai.vad.helpers import calculate_audio_rms
from app.log import get_logger

log = get_logger("app.ai.stt.recorder")


class UtteranceRef:

    __slots__ = ("_recorder", "room_id", "attempt_id", "index")

    def __init__(self, recorder: "RawAttemptRecorder", room_id: int, attempt_id: str, index: int) -> None:
        self._recorder = recorder

        self.room_id = room_id

        self.attempt_id = attempt_id

        self.index = index

    def attach(self, message_id: Optional[int], text: Optional[str]) -> None:
        self._recorder.attach_result(self, message_id, text)


class RawAttemptRecorder:
    def __init__(
        self,
        room_id: int,
        user_identity: str,
        sample_rate: int = 16000,
        channels: int = 1,
        energy_threshold: Optional[float] = None,
        end_silence_seconds: Optional[float] = None,
        max_attempt_seconds: Optional[float] = None,
        flush_bytes: Optional[int] = None,
        enabled: Optional[bool] = None,
    ) -> None:
        from app.config import settings

        self.room_id = room_id

        self.user_identity = str(user_identity)

        self.user_id = resolve_user_id(user_identity)

        self.sample_rate = sample_rate

        self.channels = channels

        if enabled is None:
            self._enabled = bool(getattr(settings, "speech_raw_enabled", True))
        else:
            self._enabled = bool(enabled)

        if energy_threshold is None:
            self._energy_threshold = float(getattr(settings, "stt_vad_energy_threshold", 0.01))
        else:
            self._energy_threshold = float(energy_threshold)

        if end_silence_seconds is None:
            self._end_silence = float(getattr(settings, "speech_raw_end_silence_seconds", 8.0))
        else:
            self._end_silence = float(end_silence_seconds)

        if max_attempt_seconds is None:
            self._max_seconds = float(getattr(settings, "speech_raw_max_attempt_seconds", 300.0))
        else:
            self._max_seconds = float(max_attempt_seconds)

        if flush_bytes is None:
            self._flush_bytes = int(getattr(settings, "speech_raw_flush_bytes", 65536))
        else:
            self._flush_bytes = int(flush_bytes)

        self._attempt_id: Optional[str] = None

        self._file = None

        self._dir: Optional[Path] = None

        self._buffer = bytearray()

        self._samples_written = 0

        self._data_bytes = 0

        self._last_voice_sample = 0

        self._started_at: Optional[str] = None

        self._utterances: List[Dict[str, Any]] = []

        self._current_utt: Optional[int] = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def samples_written(self) -> int:
        return self._samples_written

    @property
    def attempt_id(self) -> Optional[str]:
        return self._attempt_id

    @property
    def is_open(self) -> bool:
        return self._attempt_id is not None and self._file is not None

    @property
    def buffered_bytes(self) -> int:
        return len(self._buffer)

    @property
    def utterances(self) -> List[Dict[str, Any]]:
        return self._utterances

    def write_frame(self, frame) -> None:
        if not self._enabled:
            return
        try:
            pcm = normalize_pcm_int16(frame)

            if pcm is None or len(pcm) == 0:
                return
            has_voice = calculate_audio_rms(pcm) >= self._energy_threshold

            if self._file is None:
                if not has_voice:
                    return
                self.open_attempt()

            data = pcm.astype("<i2", copy=False).tobytes()

            self._buffer.extend(data)

            self._samples_written += len(pcm)

            self._data_bytes += len(data)

            if has_voice:
                self._last_voice_sample = self._samples_written
            if len(self._buffer) >= self._flush_bytes:
                self.flush()
        except Exception as error:
            log.warning(
                "Raw recorder write error | room=%s user=%s err=%s",
                self.room_id,
                self.user_identity,
                error,
            )

    def begin_utterance(self, start_sample: int) -> None:
        if not self._enabled or self._file is None:
            return
        if self._current_utt is not None:
            return
        idx = len(self._utterances)

        self._utterances.append(
            {
                "index": idx,
                "start_sample": int(start_sample),
                "end_sample": None,
                "start_sec": start_sample / self.sample_rate,
                "end_sec": None,
                "duration_sec": None,
                "message_id": None,
                "text": None,
                "status": "open",
            }
        )

        self._current_utt = idx

    def end_utterance(self, num_samples: int) -> Optional[UtteranceRef]:
        if not self._enabled or self._file is None:
            return None
        if self._current_utt is None:
            start = max(0, self._samples_written - max(0, num_samples))

            self.begin_utterance(start)

            if self._current_utt is None:
                return None
        utt = self._utterances[self._current_utt]

        start = utt.get("start_sample") or 0

        end = min(start + max(0, num_samples), self._samples_written)

        utt["end_sample"] = end

        utt["end_sec"] = end / self.sample_rate

        utt["duration_sec"] = utt["end_sec"] - (utt.get("start_sec") or 0.0)

        utt["status"] = "finalized"

        ref = UtteranceRef(self, self.room_id, self._attempt_id, utt["index"])

        self._current_utt = None

        return ref

    def abandon_utterance(self) -> None:
        if not self._enabled or self._file is None or self._current_utt is None:
            return
        utt = self._utterances[self._current_utt]

        if utt.get("end_sample") is None:
            end = self._samples_written

            utt["end_sample"] = end

            utt["end_sec"] = end / self.sample_rate

            utt["duration_sec"] = utt["end_sec"] - (utt.get("start_sec") or 0.0)

            utt["status"] = "dropped"
        self._current_utt = None

    def check_limits(self) -> None:
        if not self._enabled or self._file is None:
            return
        idle_samples = self._samples_written - self._last_voice_sample

        if idle_samples > 0 and idle_samples / self.sample_rate >= self._end_silence:
            self.close(reason="idle_silence")

            return
        if self._samples_written / self.sample_rate >= self._max_seconds:
            self.close(reason="max_duration")

    def close(self, reason: str = "stream_end") -> None:
        if not self._enabled or self._attempt_id is None or self._file is None:
            return
        try:
            if self._current_utt is not None:
                utt = self._utterances[self._current_utt]

                if utt.get("end_sample") is None:
                    end = self._samples_written

                    utt["end_sample"] = end

                    utt["end_sec"] = end / self.sample_rate

                    utt["duration_sec"] = utt["end_sec"] - (utt.get("start_sec") or 0.0)

                    utt["status"] = "truncated"
                self._current_utt = None

            self.flush()

            if self._file is not None:
                end_pos = self._file.tell()

                self._file.seek(0)

                self._file.write(wav_header(self._data_bytes, self.sample_rate, self.channels))

                self._file.seek(end_pos)

                self._file.flush()

                self._file.close()
        except Exception as error:
            log.warning(
                "Raw recorder close file error | room=%s user=%s err=%s",
                self.room_id,
                self.user_identity,
                error,
            )
        finally:
            self._file = None

        duration_sec = self._samples_written / self.sample_rate

        first = next((u for u in self._utterances if u.get("start_sec") is not None), None)

        last = next((u for u in reversed(self._utterances) if u.get("end_sec") is not None), None)

        start_sec = first["start_sec"] if first else 0.0

        end_sec = last["end_sec"] if last else duration_sec

        raw_object: Optional[str] = None

        try:
            from app.ai.stt.audio_store import object_name_for_attempt, put_audio

            raw_path = raw_audio_path(self.room_id, self._attempt_id)

            if raw_path.exists():
                raw_object = put_audio(
                    object_name_for_attempt(self.room_id, self._attempt_id),
                    raw_path.read_bytes(),
                )
        except Exception as error:
            log.warning(
                "Raw attempt MinIO upload failed | room=%s user=%s err=%s",
                self.room_id,
                self.user_identity,
                error,
            )

        metadata: Dict[str, Any] = {
            "attempt_id": self._attempt_id,
            "user_id": self.user_id,
            "user_identity": self.user_identity,
            "room_id": self.room_id,
            "raw_audio_path": f"attempts/{self._attempt_id}/raw.wav",
            "raw_audio_object": raw_object,
            "duration_sec": round(duration_sec, 3),
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "start_sec": round(start_sec, 3),
            "end_sec": round(end_sec, 3),
            "utterances": self._utterances,
            "num_utterances": len(self._utterances),
            "created_at": self._started_at,
            "closed_at": utcnow_iso(),
            "close_reason": reason,
        }

        try:
            path = metadata_path(self.room_id, self._attempt_id)

            self.write_metadata_atomic(path, metadata)
        except Exception as error:
            log.warning(
                "Raw recorder metadata write error | room=%s user=%s err=%s",
                self.room_id,
                self.user_identity,
                error,
            )

        log.debug(
            "Raw attempt closed | room=%s user=%s attempt=%s reason=%s dur=%.2fs utts=%d",
            self.room_id,
            self.user_identity,
            self._attempt_id,
            reason,
            duration_sec,
            len(self._utterances),
        )

        self._attempt_id = None

        self._dir = None

        self._buffer.clear()

        self._samples_written = 0

        self._data_bytes = 0

        self._last_voice_sample = 0

        self._started_at = None

        self._utterances = []

        self._current_utt = None

    def attach_result(self, ref: UtteranceRef, message_id: Optional[int], text: Optional[str]) -> None:
        if not self._enabled or ref is None:
            return
        try:
            if self._attempt_id == ref.attempt_id and self._attempt_id is not None:
                for utt in self._utterances:
                    if utt.get("index") == ref.index:
                        utt["message_id"] = message_id

                        utt["text"] = text

                        return
                return

            path = metadata_path(ref.room_id, ref.attempt_id)

            if not path.exists():
                return
            meta = read_attempt_metadata(path)

            if meta is None:
                return
            for utt in meta.get("utterances", []):
                if utt.get("index") == ref.index:
                    utt["message_id"] = message_id

                    utt["text"] = text

                    break
            else:
                return
            self.write_metadata_atomic(path, meta)
        except Exception as error:
            log.warning(
                "Raw recorder attach result error | room=%s user=%s err=%s",
                self.room_id,
                self.user_identity,
                error,
            )

    def open_attempt(self) -> None:
        ts = int(time.time() * 1000)

        user_tag = str(self.user_id) if self.user_id is not None else (self.user_identity or "unknown")

        user_tag = user_tag.replace(":", "_")[:32]

        self._attempt_id = f"u{user_tag}_{ts}_{uuid.uuid4().hex[:6]}"

        self._dir = attempt_dir(self.room_id, self._attempt_id)

        self._file = open(raw_audio_path(self.room_id, self._attempt_id), "wb")

        self._file.write(wav_header(0, self.sample_rate, self.channels))

        self._file.flush()

        self._buffer.clear()

        self._samples_written = 0

        self._data_bytes = 0

        self._last_voice_sample = 0

        self._started_at = utcnow_iso()

        self._utterances = []

        self._current_utt = None

        log.debug(
            "Raw attempt started | room=%s user=%s attempt=%s",
            self.room_id,
            self.user_identity,
            self._attempt_id,
        )

    def flush(self) -> None:
        if self._file is None or not self._buffer:
            return
        self._file.write(bytes(self._buffer))

        end_pos = self._file.tell()

        self._file.seek(0)

        self._file.write(wav_header(self._data_bytes, self.sample_rate, self.channels))

        self._file.seek(end_pos)

        self._file.flush()

        self._buffer.clear()

    @staticmethod
    def write_metadata_atomic(path: Path, metadata: Dict[str, Any]) -> None:
        tmp = path.with_name(path.name + ".tmp")

        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(metadata, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)


def read_attempt_metadata(meta_file: Path) -> Optional[dict]:
    try:
        with open(meta_file, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def find_attempt_by_message(
    room_id: int, user_id: Any, message_id: int
) -> Optional[Dict[str, Any]]:
    try:
        root = attempts_root(room_id)
    except Exception:
        return None
    uid = str(user_id) if user_id is not None else None

    for meta_file in sorted(root.glob("*/metadata.json")):
        meta = read_attempt_metadata(meta_file)

        if meta is None:
            continue
        if uid is not None and str(meta.get("user_id")) != uid:
            if str(meta.get("user_identity")) != uid:
                continue
        utts = meta.get("utterances", []) or []

        ordered = sorted(utts, key=lambda x: x.get("index", 0))

        mids = [u.get("message_id") for u in ordered]

        if message_id in mids:
            raw = meta_file.parent / "raw.wav"

            return {
                "attempt_id": meta.get("attempt_id") or meta_file.parent.name,
                "raw_path": raw if raw.exists() else None,
                "raw_object": meta.get("raw_audio_object"),
                "utterances": ordered,
                "message_ids": mids,
            }
    return None

