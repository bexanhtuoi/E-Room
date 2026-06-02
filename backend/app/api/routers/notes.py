from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.api.dependencies import get_current_user, get_db_session
from app.service.conversation import SessionNoteService

router = APIRouter()


@router.get("", response_model=list[dict])
async def list_notes(
    session: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    note_service = SessionNoteService(session)
    notes = note_service.list_for_user(UUID(current_user["id"]))
    return [
        {
            "id": str(n.id),
            "title": n.title,
            "created_at": n.created_at.isoformat() if n.created_at else "",
            "session_topic": "",
            "content": n.content,
            "tags": n.tags,
        }
        for n in notes
    ]


@router.get("/{note_id}")
async def get_note(
    note_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    note_service = SessionNoteService(session)
    note = note_service.get_user_note(note_id, UUID(current_user["id"]))
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return {
        "id": str(note.id),
        "title": note.title,
        "created_at": note.created_at.isoformat() if note.created_at else "",
        "session_topic": "",
        "content": note.content,
        "tags": note.tags,
    }


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> None:
    note_service = SessionNoteService(session)
    note = note_service.get_user_note(
        note_id, UUID(current_user["id"])
    )
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        )
    note_service.delete(note)
