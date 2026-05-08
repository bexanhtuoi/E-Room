from __future__ import annotations

from app.model import Session, SessionNote
from app.service.base import BaseService


class SessionService(BaseService[Session]):
    def list_sessions_for_user(self, user_id: str) -> list[Session]:
        return [session for session in self.list_all() if session.user_id == user_id]

    def attach_review(self, session_id: str, review_payload: dict[str, str | int | float | list[str] | None]) -> Session | None:
        session = self.get_by_id(session_id)
        if session is None:
            return None
        session.ai_review = review_payload
        return self.save(session)


class SessionNoteService(BaseService[SessionNote]):
    def list_notes_for_user(self, user_id: str) -> list[SessionNote]:
        return [note for note in self.list_all() if note.user_id == user_id]

    def create_note(self, note: SessionNote) -> SessionNote:
        note.word_count = len(note.content.split())
        return self.save(note)
