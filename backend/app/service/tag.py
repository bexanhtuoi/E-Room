from __future__ import annotations

from sqlmodel import Session, select

from app.model import Tag, UserTag
from app.service.base import BaseService


class TagService(BaseService[Tag]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Tag)

    def search_tags(self, query: str, limit: int = 10) -> list[Tag]:
        statement = select(Tag).where(Tag.name.contains(query)).limit(limit)
        return list(self.session.exec(statement))

    def get_popular_tags(self, limit: int = 10) -> list[Tag]:
        statement = select(Tag).order_by(Tag.usage_count.desc()).limit(limit)
        return list(self.session.exec(statement))


class UserTagService(BaseService[UserTag]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, UserTag)

    def list_user_tags(self, user_id: str) -> list[UserTag]:
        statement = select(UserTag).where(UserTag.user_id == user_id)
        return list(self.session.exec(statement))

    def attach_tag(self, user_tag: UserTag) -> UserTag:
        return self.save(user_tag)
