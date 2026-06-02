from __future__ import annotations

from uuid import UUID

from sqlmodel import Session as DBSession, select

from app.model import Session, SessionNote
from app.service.base import CRUDRepository


class SessionService(CRUDRepository):
    def __init__(self, session: DBSession) -> None:
        self.session = session
        super().__init__(Session)

    def get_by_id(self, id: UUID) -> Session | None:
        return self.session.get(self._model, id)

    def list_sessions_for_user(self, user_id: UUID) -> list[Session]:
        statement = select(Session).where(Session.user_id == user_id)
        return list(self.session.exec(statement))

    def list_sessions_for_room(self, room_id: UUID) -> list[Session]:
        statement = select(Session).where(Session.room_id == room_id)
        return list(self.session.exec(statement))

    def get_room_user_session(self, room_id: UUID, user_id: UUID) -> Session | None:
        return self.get_one(self.session, room_id=room_id, user_id=user_id)

    def attach_review(
        self,
        session_id: UUID,
        review_payload: dict[str, str | int | float | list[str] | None],
    ) -> Session | None:
        session = self.get_by_id(session_id)
        if session is None:
            return None
        session.ai_review = review_payload
        self.session.add(session)
        self.session.commit()
        self.session.refresh(session)
        return session

    def save(self, obj: Session) -> Session:
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def list_all(self) -> list[Session]:
        return self.get_many(self.session)


class SessionNoteService(CRUDRepository):
    def __init__(self, session: DBSession) -> None:
        self.session = session
        super().__init__(SessionNote)

    def list_for_user(self, user_id: UUID) -> list[SessionNote]:
        statement = (
            select(SessionNote)
            .where(SessionNote.user_id == user_id)
            .order_by(SessionNote.created_at.desc())
        )
        return list(self.session.exec(statement))

    def get_user_note(self, note_id: UUID, user_id: UUID) -> SessionNote | None:
        return self.get_one(
            self.session,
            SessionNote.id == note_id,
            SessionNote.user_id == user_id,
        )

    def delete(self, note: SessionNote) -> None:
        self.session.delete(note)
        self.session.commit()
