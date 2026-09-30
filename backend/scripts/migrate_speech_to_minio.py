"""Upload existing local speech wav files to MinIO and point JSONL/metadata at them.

Usage (from backend/):
    uv run python scripts/migrate_speech_to_minio.py [--apply]

Without --apply it only reports what would change.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

APPLY = "--apply" in sys.argv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai.stt.audio_store import (  # noqa: E402
    S3_PREFIX,
    is_s3_ref,
    object_name_for_attempt,
    object_name_for_utterance,
    put_audio,
)
from app.ai.stt.speech_log import room_dir  # noqa: E402

BASE = room_dir(0).parent

uploaded = 0
skipped = 0
failed = 0


def migrate_utterance_wavs() -> None:
    global uploaded, skipped, failed

    for room_path in sorted(BASE.glob("room_*")):
        room_id = int(room_path.name.split("_", 1)[1])
        audio_dir = room_path / "audio"

        if not audio_dir.is_dir():
            continue

        for jsonl_path in sorted(room_path.glob("user_*.jsonl")):
            try:
                lines = jsonl_path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue

            changed = False
            out_lines = []

            for line in lines:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    out_lines.append(line)
                    continue

                ref = entry.get("audio_file")

                if not ref or is_s3_ref(ref):
                    out_lines.append(line)
                    skipped += 1
                    continue

                wav_path = room_path / ref

                if not wav_path.exists():
                    out_lines.append(line)
                    skipped += 1
                    continue

                if not APPLY:
                    out_lines.append(line)
                    skipped += 1
                    continue

                object_name = object_name_for_utterance(room_id, wav_path.name)
                new_ref = put_audio(object_name, wav_path.read_bytes())

                if new_ref is None:
                    out_lines.append(line)
                    failed += 1
                    continue

                entry["audio_file"] = new_ref
                out_lines.append(json.dumps(entry, ensure_ascii=False))
                uploaded += 1

            if APPLY and out_lines != lines:
                jsonl_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


def migrate_attempt_wavs() -> None:
    global uploaded, skipped, failed

    for meta_path in sorted(BASE.glob("room_*/attempts/*/metadata.json")):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if meta.get("raw_audio_object"):
            skipped += 1
            continue

        room_id = int(meta.get("room_id") or 0)
        attempt_id = meta.get("attempt_id") or meta_path.parent.name
        raw_path = meta_path.parent / "raw.wav"

        if not raw_path.exists():
            skipped += 1
            continue

        if not APPLY:
            skipped += 1
            continue

        new_ref = put_audio(object_name_for_attempt(room_id, attempt_id), raw_path.read_bytes())

        if new_ref is None:
            failed += 1
            continue

        meta["raw_audio_object"] = new_ref
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        uploaded += 1


migrate_utterance_wavs()
migrate_attempt_wavs()
print(f"mode={'apply' if APPLY else 'dry-run'} uploaded={uploaded} skipped={skipped} failed={failed}")
