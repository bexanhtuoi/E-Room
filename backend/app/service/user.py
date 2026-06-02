from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from app.model import User
from app.service.base import CRUDRepository


class UserService(CRUDRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        super().__init__(User)

    def get_by_id(self, id: UUID) -> User | None:
        return self.session.get(self._model, id)

    def get_by_email(self, email: str) -> User | None:
        return self.get_one(self.session, email=email)

    def create_user(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def update_profile(self, user: User, update_data: dict) -> User:
        for field, value in update_data.items():
            setattr(user, field, value)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def get_users_batch(self, user_ids: list[UUID]) -> dict[str, str]:
        """Return {user_id_str: display_name} for a list of user ids."""
        if not user_ids:
            return {}
        users = self.session.exec(
            select(User).where(User.id.in_(user_ids))
        ).all()
        return {str(u.id): u.display_name for u in users}
