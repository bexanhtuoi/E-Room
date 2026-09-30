"""Move flat documents/* objects to documents/room_{id}/* (or documents/general/*).

Usage (from backend/):
    uv run python scripts/migrate_documents_to_room_prefix.py [--apply]

Without --apply it only reports what would change.
"""

from __future__ import annotations

import sys
from pathlib import Path

APPLY = "--apply" in sys.argv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select  # noqa: E402

from app.database import engine  # noqa: E402
from app.integration.minio import delete_object, get_minio_client  # noqa: E402
from app.models.document import Document  # noqa: E402
from app.config import settings  # noqa: E402

moved = 0
skipped = 0
failed = 0

with Session(engine) as db:
    docs = db.exec(select(Document).where(Document.file_path != "")).all()

    for doc in docs:
        old = doc.file_path or ""

        if not old.startswith("documents/") or old.count("/") > 1:
            skipped += 1
            continue

        filename = old.split("/", 1)[1]
        scope = f"room_{doc.room_id}" if doc.room_id is not None else "general"
        new = f"documents/{scope}/{filename}"

        if not APPLY:
            print(f"would move: {old} -> {new}")
            skipped += 1
            continue

        try:
            from minio.commonconfig import CopySource

            client = get_minio_client()
            copied = client.copy_object(
                settings.minio_bucket, new,
                CopySource(settings.minio_bucket, old),
            )
            doc.file_path = new
            db.add(doc)
            db.commit()
            delete_object(old)
            print(f"moved: {old} -> {new} ({copied.object_name})")
            moved += 1
        except Exception as error:
            db.rollback()
            print(f"FAILED: {old} err={error}")
            failed += 1

print(f"mode={'apply' if APPLY else 'dry-run'} moved={moved} skipped={skipped} failed={failed}")
