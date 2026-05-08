from __future__ import annotations

from sqlmodel import Session, select

from app.model import Tag, UserTag
from app.service.base import CRUDRepository


class TagService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = CRUDRepository(Tag)

    def get_by_id(self, id):
        return self.session.get(self.repo._model, id)

    def search_tags(self, query: str, limit: int = 10) -> list[Tag]:
        statement = select(Tag).where(Tag.name.contains(query)).limit(limit)
        return list(self.session.exec(statement))

    def get_popular_tags(self, limit: int = 10) -> list[Tag]:
        statement = select(Tag).order_by(Tag.usage_count.desc()).limit(limit)
        return list(self.session.exec(statement))

    def save(self, obj):
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj


class UserTagService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = CRUDRepository(UserTag)

    def get_by_id(self, id):
        return self.session.get(self.repo._model, id)

    def list_user_tags(self, user_id: str) -> list[UserTag]:
        statement = select(UserTag).where(UserTag.user_id == user_id)
        return list(self.session.exec(statement))

    def attach_tag(self, user_tag: UserTag) -> UserTag:
        self.session.add(user_tag)
        self.session.commit()
        self.session.refresh(user_tag)
        return user_tag
