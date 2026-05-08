from __future__ import annotations

from sqlmodel import Session as DBSession, select

from app.model import Session, SessionNote
from app.service.base import BaseService


class SessionService(BaseService[Session]):
    def __init__(self, session: DBSession) -> None:
        super().__init__(session, Session)

    def list_sessions_for_user(self, user_id: str) -> list[Session]:
        statement = select(Session).where(Session.user_id == user_id)
        return list(self.session.exec(statement))

    def attach_review(self, session_id: str, review_payload: dict[str, str | int | float | list[str] | None]) -> Session | None:
        session = self.get_by_id(session_id)
        if session is None:
            return None
        session.ai_review = review_payload
        return self.save(session)


class SessionNoteService(BaseService[SessionNote]):
    def __init__(self, session: DBSession) -> None:
        super().__init__(session, SessionNote)

    def list_notes_for_user(self, user_id: str) -> list[SessionNote]:
        statement = select(SessionNote).where(SessionNote.user_id == user_id)
        return list(self.session.exec(statement))

    def create_note(self, note: SessionNote) -> SessionNote:
        note.word_count = len(note.content.split())
        return self.save(note)
