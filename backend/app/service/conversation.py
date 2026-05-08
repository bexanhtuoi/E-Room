from __future__ import annotations

from uuid import UUID

from sqlmodel import Session as DBSession, select

from app.model import Session, SessionNote
from app.service.base import CRUDRepository


class SessionService:
    def __init__(self, session: DBSession) -> None:
        self.session = session
        self.repo = CRUDRepository(Session)

    def get_by_id(self, id: UUID):
        return self.session.get(self.repo._model, id)

    def list_sessions_for_user(self, user_id: UUID) -> list[Session]:
        statement = select(Session).where(Session.user_id == user_id)
        return list(self.session.exec(statement))

    def list_sessions_for_room(self, room_id: UUID) -> list[Session]:
        statement = select(Session).where(Session.room_id == room_id)
        return list(self.session.exec(statement))

    def attach_review(self, session_id: UUID, review_payload: dict[str, str | int | float | list[str] | None]) -> Session | None:
        session = self.get_by_id(session_id)
        if session is None:
            return None
        session.ai_review = review_payload
        self.session.add(session)
        self.session.commit()
        self.session.refresh(session)
        return session

    def save(self, obj):
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def list_all(self):
        return self.repo.get_many(self.session)


class SessionNoteService:
    def __init__(self, session: DBSession) -> None:
        self.session = session
        self.repo = CRUDRepository(SessionNote)

    def get_by_id(self, id: UUID):
        return self.session.get(self.repo._model, id)

    def list_notes_for_user(self, user_id: UUID) -> list[SessionNote]:
        statement = select(SessionNote).where(SessionNote.user_id == user_id)
        return list(self.session.exec(statement))

    def create_note(self, note: SessionNote) -> SessionNote:
        note.word_count = len(note.content.split())
        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)
        return note
